"""
core/spectral_cutoff.py — Pillar 2: High-RMS Frame Selection & STFT Cutoff Detector.

Pipeline:
  1. Slice float32 mono into 1-second frames; compute RMS per frame.
  2. Keep top-20% highest-RMS frames (≥5) to avoid detecting cutoff in silence.
  3. Compute STFT (Hann window, resolution ≈10 Hz).
  4. Build 95th-percentile spectral profile across selected frames.
  5. Smooth with Savitzky-Golay, then scan for brickwall drops from 21.5 kHz → 11 kHz.
  6. Map detected cutoff to a known encoder fingerprint.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from scipy import signal
from scipy.signal import savgol_filter

from config import (
    BRICKWALL_MIN_DROP_DB,
    BRICKWALL_MIN_SLOPE_DB_PER_KHZ,
    BRICKWALL_WIDE_DROP_DB,
    CUTOFF_SEARCH_HIGH_HZ,
    CUTOFF_SEARCH_LOW_HZ,
    CUTOFF_WINDOW_HZ,
    ENCODER_BANDS,
    SAVGOL_POLY,
    SAVGOL_WINDOW,
    SPECTRAL_PERCENTILE,
    STFT_NOVERLAP_HIGH,
    STFT_NOVERLAP_LOW,
    STFT_NPERSEG_HIGH,
    STFT_NPERSEG_LOW,
    STOPBAND_MAX_ENERGY_DB,
    STOPBAND_MAX_STD_DB,
    STOPBAND_PASSBAND_DELTA_DB,
    STUDIO_FILTER_MAX_HZ,
    STUDIO_FILTER_MIN_HZ,
)
from schemas import SpectralCutoffSchema

logger = logging.getLogger(__name__)


def _select_high_rms_frames(
    mono: np.ndarray,
    sample_rate: int,
    top_fraction: float = 0.20,
    min_frames: int = 5,
) -> np.ndarray:
    """Return concatenated top-RMS 1-second frames from *mono*."""
    frame_len = sample_rate  # 1 second
    n_frames  = len(mono) // frame_len
    if n_frames == 0:
        return mono

    frames = mono[: n_frames * frame_len].reshape(n_frames, frame_len)
    rms    = np.sqrt(np.mean(frames**2, axis=1))
    k      = max(min_frames, int(np.ceil(n_frames * top_fraction)))
    k      = min(k, n_frames)
    top_idx = np.argsort(rms)[-k:]
    return frames[top_idx].ravel()


def compute_stft_profile(
    mono: np.ndarray,
    sample_rate: int,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Compute the STFT spectral profile based on Top-N% High-Energy Frames (10–20 kHz).
    This prevents quiet passages from drowning out rare moments of high-frequency instruments.

    Returns:
        freqs  : frequency bins in Hz
        profile: dBFS values per bin across top-energy frames
    """
    if sample_rate <= 48_000:
        nperseg  = STFT_NPERSEG_LOW
        noverlap = STFT_NOVERLAP_LOW
    else:
        nperseg  = STFT_NPERSEG_HIGH
        noverlap = STFT_NOVERLAP_HIGH

    nperseg  = min(nperseg, len(mono))
    noverlap = min(noverlap, nperseg - 1)

    freqs, _, Zxx = signal.stft(
        mono, fs=sample_rate,
        window="hann",
        nperseg=nperseg,
        noverlap=noverlap,
    )

    magnitude_db = 20.0 * np.log10(np.maximum(np.abs(Zxx), 1e-7))
    nyquist = sample_rate / 2.0

    # Top-N% High-Energy Frames selection on 10-20 kHz band:
    hf_band = (freqs >= 10_000.0) & (freqs <= min(20_000.0, nyquist))
    if hf_band.sum() > 0:
        frame_hf_energy = np.percentile(magnitude_db[hf_band, :], 85, axis=0)
    else:
        frame_hf_energy = np.mean(magnitude_db, axis=0)

    total_frames = magnitude_db.shape[1]
    # Lấy top 10% khung thời gian có năng lượng dải 10-20 kHz mạnh nhất
    k_frames = max(10, int(np.ceil(total_frames * 0.10)))
    k_frames = min(k_frames, total_frames)

    top_indices = np.argsort(frame_hf_energy)[-k_frames:]
    top_frames_mag = magnitude_db[:, top_indices]

    profile = np.percentile(top_frames_mag, 90, axis=1)

    return freqs, profile


def _find_brickwall_cutoff(
    freqs: np.ndarray,
    smoothed: np.ndarray,
    nyquist: float,
) -> Tuple[Optional[float], Optional[float]]:
    """
    Robust Brickwall Cutoff Detection for MP3/AAC/Opus/Vorbis lowpass filters.

    Scans from CUTOFF_SEARCH_HIGH_HZ down to CUTOFF_SEARCH_LOW_HZ looking
    for a characteristic lossy codec cliff:
      1. Steep descent: >= BRICKWALL_MIN_DROP_DB drop across 1000 Hz or >= BRICKWALL_WIDE_DROP_DB across 1600 Hz.
      2. Stopband attenuation: Average energy above cutoff is at least STOPBAND_PASSBAND_DELTA_DB
         below the passband, and does not exceed STOPBAND_MAX_ENERGY_DB.
    """
    delta_hz = freqs[1] - freqs[0]

    f_start = min(CUTOFF_SEARCH_HIGH_HZ, nyquist * 0.998)
    f_end   = CUTOFF_SEARCH_LOW_HZ

    search_indices = np.where((freqs >= f_end) & (freqs <= f_start))[0]
    if len(search_indices) == 0:
        return None, None

    w_500 = max(1, int(500.0 / delta_hz))
    w_800 = max(1, int(800.0 / delta_hz))

    for idx in search_indices[::-1]:
        f = freqs[idx]

        lo_500 = max(0, idx - w_500)
        hi_500 = min(len(freqs) - 1, idx + w_500)
        drop_500 = smoothed[lo_500] - smoothed[hi_500]

        lo_800 = max(0, idx - w_800)
        hi_800 = min(len(freqs) - 1, idx + w_800)
        drop_800 = smoothed[lo_800] - smoothed[hi_800]

        # Must have significant drop
        if drop_500 < BRICKWALL_MIN_DROP_DB and drop_800 < BRICKWALL_WIDE_DROP_DB:
            continue

        offset_hz = min(400.0, max(40.0, (nyquist - f) * 0.35))
        above_mask = freqs > (f + offset_hz)
        min_bins = 3 if f >= 21_000.0 else 5
        if above_mask.sum() < min_bins:
            continue

        mean_above   = float(np.mean(smoothed[above_mask]))
        std_above    = float(np.std(smoothed[above_mask]))
        energy_below = max(float(smoothed[lo_500]), float(smoothed[lo_800]))

        # Stopband verification:
        if (energy_below - mean_above) < STOPBAND_PASSBAND_DELTA_DB:
            continue
        if mean_above > STOPBAND_MAX_ENERGY_DB:
            continue
        if std_above > STOPBAND_MAX_STD_DB:
            continue

        # Refine cutoff to the steepest descent point
        lo_refine = max(0, idx - w_800)
        hi_refine = min(len(freqs) - 1, idx + w_800)
        if hi_refine - lo_refine < 3:
            continue
        local_deriv = np.gradient(smoothed[lo_refine:hi_refine], delta_hz) * 1000.0
        steepest_rel = int(np.argmin(local_deriv))
        refined_idx = lo_refine + steepest_rel
        refined_f = float(freqs[refined_idx])
        slope_db_per_khz = float(local_deriv[steepest_rel])

        # Require true brickwall steepness (steeper than -20 dB/kHz)
        # to prevent gentle natural acoustic roll-offs from being falsely classified
        if slope_db_per_khz > BRICKWALL_MIN_SLOPE_DB_PER_KHZ:
            continue

        return refined_f, slope_db_per_khz

    return None, None


def _map_encoder(cutoff_hz: Optional[float]) -> Optional[str]:
    if cutoff_hz is None:
        return None
    for lo, hi, label in ENCODER_BANDS:
        if lo <= cutoff_hz <= hi:
            return label
    return None


def analyze_spectral_cutoff(
    float32_mono: np.ndarray,
    sample_rate: int,
) -> Tuple[SpectralCutoffSchema, np.ndarray, np.ndarray]:
    """
    Full cutoff detection using Top-N% High-Energy Frames and Golden Rule verification.

    Returns:
        schema   : SpectralCutoffSchema
        freqs    : frequency bins (Hz) for visualisation
        profile  : smoothed spectral profile (dBFS)
    """
    nyquist = sample_rate / 2.0

    if sample_rate <= 48_000:
        nperseg  = STFT_NPERSEG_LOW
        noverlap = STFT_NOVERLAP_LOW
    else:
        nperseg  = STFT_NPERSEG_HIGH
        noverlap = STFT_NOVERLAP_HIGH

    nperseg  = min(nperseg, len(float32_mono))
    noverlap = min(noverlap, nperseg - 1)

    freqs, _, Zxx = signal.stft(
        float32_mono, fs=sample_rate,
        window="hann",
        nperseg=nperseg,
        noverlap=noverlap,
    )
    magnitude_db = 20.0 * np.log10(np.maximum(np.abs(Zxx), 1e-7))

    # ── 1. Top-N% High-Energy Frames (10–20 kHz) ─────────────────────────────
    # Thay vì cộng trung bình toàn bộ bài làm đoạn im lặng dìm chết âm sắc cao,
    # chỉ chọn top 10% các khung thời gian có năng lượng dải 10–20 kHz mạnh nhất để tìm cutoff.
    hf_band = (freqs >= 10_000.0) & (freqs <= min(20_000.0, nyquist))
    if hf_band.sum() > 0:
        frame_hf_energy = np.percentile(magnitude_db[hf_band, :], 85, axis=0)
    else:
        frame_hf_energy = np.mean(magnitude_db, axis=0)

    total_frames = magnitude_db.shape[1]
    k_frames = max(10, int(np.ceil(total_frames * 0.10)))
    k_frames = min(k_frames, total_frames)

    top_indices = np.argsort(frame_hf_energy)[-k_frames:]
    top_frames_mag = magnitude_db[:, top_indices]
    profile = np.percentile(top_frames_mag, 90, axis=1)

    smoothed = savgol_filter(profile, window_length=SAVGOL_WINDOW, polyorder=SAVGOL_POLY)
    cutoff_hz, slope = _find_brickwall_cutoff(freqs, smoothed, nyquist)

    # ── 2. Quy tắc vàng (Golden Rule): ───────────────────────────────────────
    # Trong một file âm thanh, chỉ cần tồn tại dù chỉ 1–2 giây có tín hiệu âm nhạc tự nhiên
    # (không phải nhiễu trắng/glitch) vươn lên tới 20–21 kHz, thì trần tần số thực sự của file
    # đó là 20–21 kHz, bất chấp 99% thời gian còn lại nó chỉ nằm ở 15–18 kHz.
    ultra_mask = (freqs >= 19_800.0) & (freqs <= min(21_800.0, nyquist))
    mid_mask = (freqs >= 3_000.0) & (freqs <= 8_000.0)
    has_golden_rule_reach = False
    active_ultra_seconds = 0.0

    if ultra_mask.sum() > 0 and mid_mask.sum() > 0:
        ultra_energy_t = np.percentile(magnitude_db[ultra_mask, :], 85, axis=0)
        mid_energy_t = np.percentile(magnitude_db[mid_mask, :], 85, axis=0)

        # Frame âm nhạc tự nhiên vươn tới 20-21 kHz: có năng lượng dải siêu cao (> -75 dBFS)
        # và đồng thời có âm lượng dải trung (> -52 dBFS) xác nhận là âm sắc nhạc cụ thực tế.
        musical_frames = (ultra_energy_t > -75.0) & (mid_energy_t > -52.0)
        active_count = int(np.sum(musical_frames))
        frame_dt = (nperseg - noverlap) / sample_rate
        active_ultra_seconds = active_count * frame_dt

        # Chỉ cần >= 0.5 - 1.0 giây có âm thanh thực sự vươn tới 20-21 kHz:
        if active_ultra_seconds >= 0.5:
            has_golden_rule_reach = True

    if has_golden_rule_reach and (cutoff_hz is None or cutoff_hz < 20_500.0):
        # Trần tần số thực tế đạt 20–21 kHz! Bác bỏ bất kỳ cutoff thấp nào ở các đoạn êm dịu.
        cutoff_hz = None
        slope = None
        is_brickwall = False
        is_studio_filter = True
        encoder = "Studio Anti-Aliasing Filter (Redbook CD)"
        detail = (
            f"Quy tắc vàng: Tín hiệu âm nhạc tự nhiên vươn tới dải 20–21 kHz tại các đoạn cao trào "
            f"({active_ultra_seconds:.1f}s hoạt động). "
            "Trần tần số thực tế của bản thu đạt chuẩn phòng thu (>20 kHz), không bị cắt gọt lossy."
        )
    else:
        # Kiểm tra Bộ lọc phòng thu thông thường gần Nyquist
        is_studio_filter = False
        if cutoff_hz is not None:
            is_studio_range = (
                (STUDIO_FILTER_MIN_HZ <= cutoff_hz <= STUDIO_FILTER_MAX_HZ)
                if sample_rate <= 44_100
                else (cutoff_hz >= nyquist * 0.95)
            )
            if is_studio_range:
                is_studio_filter = True

        is_brickwall = (cutoff_hz is not None) and (not is_studio_filter)
        encoder = _map_encoder(cutoff_hz)
        if is_studio_filter:
            encoder = "Studio Anti-Aliasing Filter (Redbook CD)"

        # detail string
        if is_studio_filter and cutoff_hz is not None:
            slope_val = slope if slope is not None else 0.0
            detail = (
                f"Studio anti-aliasing filter detected at {cutoff_hz/1000:.2f} kHz "
                f"(slope {slope_val:.1f} dB/kHz) near Nyquist boundary ({nyquist/1000:.2f} kHz). "
                f"Preserves genuine Redbook CD audio bandwidth."
            )
        elif is_brickwall and cutoff_hz is not None:
            slope_val = slope if slope is not None else 0.0
            detail = (
                f"Brickwall cutoff detected at {cutoff_hz/1000:.2f} kHz "
                f"(slope {slope_val:.1f} dB/kHz). "
                f"Suspected source: {encoder or 'unknown encoder'}."
            )
        else:
            detail = f"No brickwall cutoff found up to Nyquist ({nyquist/1000:.1f} kHz). Full-spectrum audio."

    # Đo năng lượng tổng thể dải 14–20 kHz để phục vụ Gatekeeping với MDCT:
    band_14_20 = (freqs >= 14_000.0) & (freqs <= min(20_000.0, nyquist))
    hf_energy_14_20 = float(np.mean(smoothed[band_14_20])) if band_14_20.sum() > 0 else -100.0

    return (
        SpectralCutoffSchema(
            nyquist_hz=nyquist,
            detected_cutoff_hz=cutoff_hz,
            rolloff_slope_db_per_khz=slope,
            is_brickwall=is_brickwall,
            is_studio_filter=is_studio_filter,
            suspected_source_encoder=encoder,
            detail=detail,
            hf_energy_14_20_db=round(hf_energy_14_20, 2),
        ),
        freqs,
        smoothed,
    )
