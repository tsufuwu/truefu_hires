"""
core/anti_spoof.py — Pillar 3: Spectral Holes & Fake Noise Detector.

Test A — MDCT Spectral Holes (12 kHz–16 kHz sparsity)
    Lossy codecs leave quantisation-zero bins ("swiss-cheese" pattern).
    If >38% of time-frequency bins in 12–16 kHz drop ≥35 dB below the
    local median, it's likely MDCT-compressed audio.

Test B — High-Frequency Temporal Envelope Correlation
    Genuine recordings: HF energy (16.5–21.5 kHz) co-moves with
    upper-mid transients (3–8 kHz) because real cymbals/sibilance cause both.
    Fake noise injection: HF is stationary (low σ) and uncorrelated (low r).
"""
from __future__ import annotations

import logging
from typing import Optional, Tuple

import numpy as np
from scipy.signal import savgol_filter
from scipy.stats import pearsonr

from config import (
    CORRELATION_THRESH,
    HF_BAND_HIGH_HZ,
    HF_BAND_LOW_HZ,
    HF_ENERGY_FLOOR_DB,
    HF_STDEV_THRESH_DB,
    HOLE_BAND_HIGH_HZ,
    HOLE_BAND_LOW_HZ,
    HOLE_DROP_DB,
    HOLE_RATIO_THRESH,
    MID_BAND_HIGH_HZ,
    MID_BAND_LOW_HZ,
    STFT_NOVERLAP_LOW,
    STFT_NPERSEG_LOW,
)
from schemas import AntiSpoofSchema

logger = logging.getLogger(__name__)


def _band_mask(freqs: np.ndarray, low_hz: float, high_hz: float) -> np.ndarray:
    return (freqs >= low_hz) & (freqs <= high_hz)


def _band_energy_envelope(
    magnitude_db: np.ndarray,  # shape (freq_bins, time_frames)
    freqs: np.ndarray,
    low_hz: float,
    high_hz: float,
    percentile: float = 90.0,
) -> np.ndarray:
    """90th-percentile dBFS energy per time-frame within [low_hz, high_hz].
    Using high percentile instead of mean so sparse injected noise (few active
    bins) is still detected when those bins peak above the floor."""
    mask = _band_mask(freqs, low_hz, high_hz)
    if mask.sum() == 0:
        return np.zeros(magnitude_db.shape[1])
    return np.percentile(magnitude_db[mask, :], percentile, axis=0)


def analyze_anti_spoof(
    float32_mono: np.ndarray,
    sample_rate: int,
    freqs: np.ndarray,            # from spectral_cutoff module (reuse STFT)
    smoothed_profile: np.ndarray, # 95th-percentile profile (already computed)
    stft_magnitude_db: Optional[np.ndarray] = None,  # full time-freq matrix
) -> AntiSpoofSchema:
    """
    Perform both anti-spoof tests.

    Args:
        float32_mono       : normalised mono signal
        sample_rate        : Hz
        freqs              : frequency bins from prior STFT
        smoothed_profile   : 95th-percentile smoothed profile (dBFS)
        stft_magnitude_db  : (freq_bins, time_frames) dBFS matrix; re-computed if None
    """
    from scipy import signal as sp_signal

    # ── Compute full STFT if not provided ───────────────────────────────────
    if stft_magnitude_db is None:
        nperseg  = STFT_NPERSEG_LOW if sample_rate <= 48_000 else 8192
        noverlap = STFT_NOVERLAP_LOW if sample_rate <= 48_000 else 4096
        nperseg  = min(nperseg, len(float32_mono))
        noverlap = min(noverlap, nperseg - 1)
        _, _, Zxx = sp_signal.stft(
            float32_mono, fs=sample_rate,
            window="hann", nperseg=nperseg, noverlap=noverlap,
        )
        stft_magnitude_db = 20.0 * np.log10(np.maximum(np.abs(Zxx), 1e-7))

    nyquist = sample_rate / 2.0

    # ════════════════════════════════════════════════════════════════════════
    # Test A: Spectral Holes in 12 kHz – 16 kHz (Chống bắt nhầm nhạc ngắt quãng)
    # ════════════════════════════════════════════════════════════════════════
    # Chỉ đếm một ô thời gian-tần số ở dải 12–16 kHz là "Lỗ nén MDCT" khi và chỉ khi:
    # Cùng tại frame thời gian đó, dải tần thấp-trung (1 kHz – 8 kHz) đang có năng lượng cao
    # (> -40 dBFS), nhưng dải 12–16 kHz lại bị khoét rỗng cục bộ (band-stop drop > 35 dB
    # so với các bin tần số lân cận).
    hole_mask = _band_mask(freqs, HOLE_BAND_LOW_HZ, min(HOLE_BAND_HIGH_HZ, nyquist))
    mid_active_mask = _band_mask(freqs, 1000.0, 8000.0)

    if hole_mask.sum() < 2 or mid_active_mask.sum() == 0:
        spectral_holes_ratio = 0.0
        holes_detected       = False
    else:
        # Năng lượng dải thấp-trung (1–8 kHz) theo từng frame thời gian
        frame_mid_energy = np.percentile(stft_magnitude_db[mid_active_mask, :], 85, axis=0)
        active_frames = frame_mid_energy > -40.0

        if active_frames.sum() < 5:
            # Nhạc quá thưa hoặc không có frame nào đủ năng lượng > -40 dBFS
            spectral_holes_ratio = 0.0
            holes_detected       = False
        else:
            # Chỉ xét trên các frame đang có âm nhạc hoạt động mạnh:
            sub_band = stft_magnitude_db[hole_mask, :][:, active_frames]  # (F_hole, T_active)

            # Tính baseline lân cận trong cùng frame (so với trung bình dải lân cận ngay trên/dưới)
            # hoặc rolling median theo trục tần số:
            from scipy.ndimage import uniform_filter1d
            # Filter trên dải 12-16k để tìm đường bao cục bộ
            local_context = uniform_filter1d(sub_band, size=5, axis=0, mode="nearest")
            # Điểm rơi cục bộ: năng lượng tụt sâu > 35 dB so với lân cận hoặc so với mức trung vị frame
            frame_medians = np.median(sub_band, axis=0, keepdims=True)
            reference_energy = np.maximum(local_context, frame_medians)

            drop_mask = (reference_energy - sub_band) > HOLE_DROP_DB
            spectral_holes_ratio = float(drop_mask.mean())
            holes_detected = spectral_holes_ratio > HOLE_RATIO_THRESH
            logger.debug(
                "Spectral holes (active frames=%d): ratio=%.3f, threshold=%.2f, detected=%s",
                int(active_frames.sum()), spectral_holes_ratio, HOLE_RATIO_THRESH, holes_detected,
            )

    # ════════════════════════════════════════════════════════════════════════
    # Test B: HF Temporal Envelope Correlation & Anti-Tape-Hiss Guard
    # ════════════════════════════════════════════════════════════════════════
    hf_mask  = _band_mask(freqs, HF_BAND_LOW_HZ,  min(HF_BAND_HIGH_HZ, nyquist))
    mid_mask = _band_mask(freqs, MID_BAND_LOW_HZ, MID_BAND_HIGH_HZ)

    fake_noise_injected    = False
    hf_envelope_correlation: Optional[float] = None

    if hf_mask.sum() == 0:
        detail_b = "HF band (16.5–21.5 kHz) not present (sample rate too low)."
    else:
        hf_env  = _band_energy_envelope(stft_magnitude_db, freqs, HF_BAND_LOW_HZ, min(HF_BAND_HIGH_HZ, nyquist), percentile=99.0)
        mid_env = _band_energy_envelope(stft_magnitude_db, freqs, MID_BAND_LOW_HZ, MID_BAND_HIGH_HZ, percentile=99.0)

        mean_hf = float(hf_env.mean())
        # Use global max across all HF freq×time bins as the presence test
        hf_raw_mask = _band_mask(freqs, HF_BAND_LOW_HZ, min(HF_BAND_HIGH_HZ, nyquist))
        peak_hf = float(stft_magnitude_db[hf_raw_mask, :].max()) if hf_raw_mask.sum() > 0 else mean_hf
        std_hf  = float(hf_env.std())

        # Use peak (rather than mean) so sparse injected noise is not missed
        if peak_hf <= HF_ENERGY_FLOOR_DB:
            detail_b = "No detectable energy above 16.5 kHz — natural roll-off."
        else:
            # Compute Pearson r
            if len(hf_env) > 2 and np.std(hf_env) > 0 and np.std(mid_env) > 0:
                r_val, _ = pearsonr(mid_env, hf_env)
                hf_envelope_correlation = float(r_val)
            else:
                hf_envelope_correlation = 1.0  # insufficient data → assume genuine

            if hf_envelope_correlation < CORRELATION_THRESH and std_hf < HF_STDEV_THRESH_DB:
                # ── Kiểm tra chống bắt nhầm tiếng xì băng từ (Analog Tape Hiss) ──
                # Đặc tính Tape Hiss: Nền nhiễu thực tế tồn tại xuyên suốt cả ở dải trung (1–8 kHz)
                # và dải cao (>16.5 kHz) ở mức -75 đến -88 dBFS (không phải digital silence <-92 dBFS),
                # và phổ tần suy giảm mượt (smooth roll-off), không có bước nhảy đột biến (step shelf).
                mid_noise_floor = float(np.percentile(stft_magnitude_db[mid_mask, :], 10))
                hf_noise_floor  = float(np.percentile(stft_magnitude_db[hf_raw_mask, :], 10))

                mid_high_mask = (freqs >= 12_000.0) & (freqs <= 16_000.0)
                profile_hf_mean = float(np.mean(smoothed_profile[hf_raw_mask])) if hf_raw_mask.sum() > 0 else -100.0
                profile_mid_high_mean = float(np.mean(smoothed_profile[mid_high_mask])) if mid_high_mask.sum() > 0 else -100.0

                is_tape_hiss = (
                    (hf_noise_floor > -92.0)
                    and (mid_noise_floor > -90.0)
                    and (abs(hf_noise_floor - mid_noise_floor) <= 12.0)
                    and (profile_hf_mean <= profile_mid_high_mean + 4.0)
                )

                if is_tape_hiss:
                    fake_noise_injected = False
                    detail_b = (
                        f"Phát hiện tiếng xì băng từ tự nhiên (Analog Tape Hiss, r={hf_envelope_correlation:.3f}, "
                        f"sàn nhiễu ~{hf_noise_floor:.1f} dBFS phân bổ đồng nhất xuyên suốt dải trung và dải cao). "
                        "Phổ suy giảm mượt, không phải bơm nhiễu nhân tạo."
                    )
                else:
                    fake_noise_injected = True
                    detail_b = (
                        f"HF energy (16.5–21.5 kHz) is stationary (σ={std_hf:.2f} dB, "
                        f"r={hf_envelope_correlation:.3f}) — consistent with injected synthetic noise."
                    )
            else:
                detail_b = (
                    f"HF envelope correlation r={hf_envelope_correlation:.3f}, "
                    f"σ={std_hf:.2f} dB — consistent with genuine transients."
                )

    # ── Composite detail ─────────────────────────────────────────────────────
    detail_a = (
        f"Spectral hole ratio in 12–16 kHz: {spectral_holes_ratio:.3f} "
        f"({'HOLES DETECTED' if holes_detected else 'clean'})."
    )
    detail = f"{detail_a} | {detail_b}"

    return AntiSpoofSchema(
        spectral_holes_ratio=round(spectral_holes_ratio, 4),
        holes_detected=holes_detected,
        hf_envelope_correlation=(
            round(hf_envelope_correlation, 4) if hf_envelope_correlation is not None else None
        ),
        fake_noise_injected=fake_noise_injected,
        detail=detail,
    )
