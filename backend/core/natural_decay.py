"""
core/natural_decay.py — Module B: Spectral Rolloff Natural Decay Rate & Knee Discontinuity.

Principle:
  Real acoustic instruments and natural vocals in an authentic recording exhibit a smooth,
  monotonic exponential decay in the upper frequencies (10 kHz -> 22 kHz), obeying physical
  acoustics without artificial slope breaks.
  Lossy encoders (MP3, AAC, etc.) pass audio through a steep lowpass filter, leaving:
  1. An unnatural "knee" (gãy khúc) at standard filter boundaries (e.g. ~16.0 kHz or ~20.0 kHz).
  2. A transition from natural roll-off into an unnaturally flat horizontal noise shelf (phẳng lì,
     near-zero slope) that violates natural acoustic decay.
"""
from __future__ import annotations

import logging
from typing import Optional, Tuple
import numpy as np
from scipy.signal import savgol_filter

from schemas import NaturalDecaySchema, SpectralCutoffSchema

logger = logging.getLogger(__name__)


def analyze_natural_decay(
    freqs: np.ndarray,
    smoothed_profile: np.ndarray,
    spectral_cutoff: Optional[SpectralCutoffSchema] = None,
) -> NaturalDecaySchema:
    """
    Analyzes the decay rate (slope in dB/kHz) and checks for physical law violations,
    abrupt slope fractures (knees), and unnatural horizontal noise shelves above 15 kHz.
    """
    nyquist = freqs[-1]
    if nyquist < 18_000.0:
        return NaturalDecaySchema(
            knee_frequency_khz=None,
            slope_pre_knee_db_per_khz=None,
            slope_post_knee_db_per_khz=None,
            decay_discontinuity_score=0.0,
            violates_natural_decay=False,
            status="PASSED",
            detail="Tần số lấy mẫu không đủ để quét vùng phân rã 10–20 kHz.",
        )

    # Work in 10 kHz to 21.5 kHz range
    eval_mask = (freqs >= 10_000.0) & (freqs <= min(21_500.0, nyquist))
    eval_freqs = freqs[eval_mask] / 1000.0  # in kHz
    eval_db = smoothed_profile[eval_mask]

    if len(eval_freqs) < 20:
        return NaturalDecaySchema(
            knee_frequency_khz=None,
            slope_pre_knee_db_per_khz=None,
            slope_post_knee_db_per_khz=None,
            decay_discontinuity_score=0.0,
            violates_natural_decay=False,
            status="PASSED",
            detail="Dữ liệu dải tần 10–20 kHz không đủ điểm phân tích.",
        )

    # Smooth the curve lightly for robust slope computation
    smooth_len = min(31, (len(eval_db) // 2) * 2 - 1)
    if smooth_len >= 7:
        smooth_db = savgol_filter(eval_db, smooth_len, 2)
    else:
        smooth_db = eval_db

    # Compute 1st derivative (slope in dB/kHz)
    df = eval_freqs[1] - eval_freqs[0]
    slopes = np.gradient(smooth_db, df)

    # Scan for knee point between 15.0 kHz and 20.5 kHz
    # A lossy filter cutoff causes:
    # 1. Very steep negative slope right around cutoff (e.g. <= -12 dB/kHz)
    # 2. Followed by a sharp leveling out (slope jumping back towards ~0 dB/kHz, flat shelf)
    knee_candidates = []

    # Test candidate points from 15.0 to min(20.5, nyquist/1000 - 0.5)
    max_scan_khz = min(20.5, (nyquist / 1000.0) - 0.5)
    scan_indices = np.where((eval_freqs >= 15.0) & (eval_freqs <= max_scan_khz))[0]

    window_pts = max(3, int(1.2 / df))  # ~1.2 kHz window

    for idx in scan_indices:
        if idx - window_pts < 0 or idx + window_pts >= len(eval_freqs):
            continue

        f_cand = eval_freqs[idx]

        # Region before: [idx - window_pts : idx]
        pre_slopes = slopes[idx - window_pts : idx]
        # Region after: [idx : idx + window_pts]
        post_slopes = slopes[idx : idx + window_pts]

        pre_slope_mean = float(np.mean(pre_slopes))
        post_slope_mean = float(np.mean(post_slopes))
        post_slope_abs = abs(post_slope_mean)

        # Pre-energy and post-energy
        post_energy = float(np.mean(smooth_db[idx : idx + window_pts]))

        # Condition for unnatural lossy knee:
        # Pre-slope is steep negative (<= -6.0 dB/kHz) or drop is steep,
        # AND post-slope suddenly flattens into a horizontal shelf (|slope| <= 2.2 dB/kHz)
        # with post-energy non-zero (between -95 dBFS and -55 dBFS).
        slope_gap = post_slope_mean - pre_slope_mean  # positive jump from steep negative to flat
        if pre_slope_mean <= -6.0 and post_slope_abs <= 2.2 and slope_gap >= 4.5 and post_energy > -95.0:
            # Score this candidate
            # Closeness to common lossy boundaries: 16.0 kHz, 18.5 kHz, 20.0 kHz
            target_dist = min(
                abs(f_cand - 16.0),
                abs(f_cand - 18.5),
                abs(f_cand - 20.0),
            )
            score = slope_gap + max(0.0, 3.0 - target_dist * 2.0)
            knee_candidates.append({
                "freq_khz": f_cand,
                "score": score,
                "pre_slope": pre_slope_mean,
                "post_slope": post_slope_mean,
                "gap": slope_gap,
                "post_energy": post_energy,
            })

    if knee_candidates:
        # Pick the most pronounced knee
        best_knee = max(knee_candidates, key=lambda x: x["score"])
        f_knee = best_knee["freq_khz"]
        pre_s = best_knee["pre_slope"]
        post_s = best_knee["post_slope"]
        gap = best_knee["gap"]

        # Check whether high frequencies above the knee maintain genuine active musical energy
        # and extend all the way past 20.5 - 21 kHz:
        hf_mask = (eval_freqs >= max(f_knee + 1.2, 17.0)) & (eval_freqs <= min(21.0, (nyquist / 1000.0) - 0.2))
        hf_energy = float(np.mean(eval_db[hf_mask])) if hf_mask.sum() > 0 else -120.0

        near_nyquist_mask = (eval_freqs >= 20.5) & (eval_freqs <= min(21.8, nyquist / 1000.0))
        near_nyquist_energy = float(np.mean(eval_db[near_nyquist_mask])) if near_nyquist_mask.sum() > 0 else -120.0

        has_studio_filter = bool(
            spectral_cutoff and (
                getattr(spectral_cutoff, "is_studio_filter", False)
                or (
                    spectral_cutoff.detected_cutoff_hz is not None
                    and spectral_cutoff.detected_cutoff_hz >= 21_000.0
                    and not spectral_cutoff.is_brickwall
                )
            )
        )

        # A true lossy codec cutoff (MP3 128k/160k at ~15-16 kHz) collapses energy into
        # the dead stopband (<-85 dBFS to -120 dBFS).
        # If the high band retains strong musical energy (above -75 dBFS) that extends continuously
        # to over 20.5-21 kHz, or if confirmed by a Studio Anti-Aliasing Filter at Nyquist,
        # this plateau is an authentic mix/mastering aesthetic characteristic (e.g. J-pop/Vocaloid
        # bright synths, cymbals, or vocal air EQ shelf), NOT lossy codec truncation.
        is_mix_quirk = (
            (hf_energy > -75.0 and near_nyquist_energy > -80.0)
            or (has_studio_filter and hf_energy > -78.0)
        )

        discontinuity_score = min(1.0, gap / 15.0)

        if is_mix_quirk:
            violates = False
            status = "PASSED"
            detail = (
                f"Phát hiện điểm gãy phổ tần tại {f_knee:.2f} kHz, tuy nhiên dải siêu cao vẫn duy trì "
                f"năng lượng thực ({hf_energy:.1f} dBFS) kéo dài liên tục tới >21 kHz (chuẩn phòng thu). "
                f"Đây là đặc thù bản phối âm nhạc thực tế (mix/mastering), không phải vết cắt nén lossy."
            )
        elif gap >= 5.0 and abs(post_s) <= 2.0:
            violates = True
            status = "FAILED"
            detail = (
                f"CẢNH BÁO: Vi phạm quy luật suy giảm tự nhiên! Phát hiện điểm gãy khúc (knee) tại {f_knee:.2f} kHz: "
                f"đang dốc {pre_s:.1f} dB/kHz thì đột ngột chuyển thành dải phẳng lì {post_s:.1f} dB/kHz "
                f"(độ gãy Δ={gap:.1f} dB/kHz). Đây là dấu vết đặc trưng của bộ lọc thông thấp (low-pass filter) từ codec nén."
            )
        else:
            violates = False
            status = "PASSED"
            detail = (
                f"Độ suy giảm phổ phù hợp quy luật vật lý (độ dốc {pre_s:.1f} dB/kHz ở dải cao, "
                f"không phát hiện gãy khúc bất thường thành dải phẳng)."
            )

        return NaturalDecaySchema(
            knee_frequency_khz=round(float(f_knee), 2),
            slope_pre_knee_db_per_khz=round(float(pre_s), 2),
            slope_post_knee_db_per_khz=round(float(post_s), 2),
            decay_discontinuity_score=round(float(discontinuity_score), 3),
            violates_natural_decay=violates,
            status=status,
            detail=detail,
        )

    # No knee detected — compute overall decay slope from 10 kHz to 20 kHz
    idx_10k = np.argmin(np.abs(eval_freqs - 10.0))
    idx_20k = np.argmin(np.abs(eval_freqs - min(20.0, nyquist / 1000.0)))
    if idx_20k > idx_10k:
        total_slope = float(
            (smooth_db[idx_20k] - smooth_db[idx_10k]) / (eval_freqs[idx_20k] - eval_freqs[idx_10k])
        )
    else:
        total_slope = float(np.mean(slopes))

    return NaturalDecaySchema(
        knee_frequency_khz=None,
        slope_pre_knee_db_per_khz=round(total_slope, 2),
        slope_post_knee_db_per_khz=None,
        decay_discontinuity_score=0.0,
        violates_natural_decay=False,
        status="PASSED",
        detail=f"Độ suy giảm năng lượng tuân theo hàm mũ tự nhiên (độ dốc trung bình {total_slope:.2f} dB/kHz).",
    )
