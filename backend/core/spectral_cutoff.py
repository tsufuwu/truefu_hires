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

    # Top-N% High-Energy Frames selection on 8-20 kHz band (chống bắt nhầm nhạc acoustic/piano):
    hf_band = (freqs >= 8_000.0) & (freqs <= min(20_000.0, nyquist))
    if hf_band.sum() > 0:
        frame_hf_energy = np.percentile(magnitude_db[hf_band, :], 90, axis=0)
    else:
        frame_hf_energy = np.mean(magnitude_db, axis=0)

    total_frames = magnitude_db.shape[1]
    # Lấy top 5% khung thời gian có năng lượng dải 8-20 kHz mạnh nhất (tối thiểu 20 frames để ổn định mẫu ngắn)
    k_frames = max(20, int(np.ceil(total_frames * 0.05)))
    k_frames = min(k_frames, total_frames)

    top_indices = np.argsort(frame_hf_energy)[-k_frames:]
    top_frames_mag = magnitude_db[:, top_indices]

    # Max-hold / 95th-percentile theo trục thời gian trên top frames
    profile = np.percentile(top_frames_mag, 95, axis=1)

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

    # ── 1. Top-N% High-Energy Frames (8–20 kHz) ──────────────────────────────
    # Chuyển sang phương pháp Top High-Energy Frames (Max-Hold / 96th Percentile theo trục thời gian).
    # Chỉ trích xuất top 5% các frame STFT có tổng năng lượng ở dải trung-cao (8 kHz – 20 kHz) lớn nhất để tìm cutoff.
    hf_band = (freqs >= 8_000.0) & (freqs <= min(20_000.0, nyquist))
    if hf_band.sum() > 0:
        frame_hf_energy = np.percentile(magnitude_db[hf_band, :], 90, axis=0)
    else:
        frame_hf_energy = np.mean(magnitude_db, axis=0)

    total_frames = magnitude_db.shape[1]
    k_frames = max(20, int(np.ceil(total_frames * 0.05)))
    k_frames = min(k_frames, total_frames)

    top_indices = np.argsort(frame_hf_energy)[-k_frames:]
    top_frames_mag = magnitude_db[:, top_indices]
    profile = np.percentile(top_frames_mag, 95, axis=1)

    smoothed = savgol_filter(profile, window_length=SAVGOL_WINDOW, polyorder=SAVGOL_POLY)
    cutoff_hz, slope = _find_brickwall_cutoff(freqs, smoothed, nyquist)

    # ── 2. Quy tắc đỉnh cục bộ (Local Peak Override): ─────────────────────────
    # Quét qua toàn bộ thời lượng file, nếu tồn tại ít nhất một cụm frame liên tiếp
    # (kéo dài >= 150ms) có năng lượng âm nhạc hợp lệ (không phải click/glitch ở đầu/cuối file)
    # vươn lên ngưỡng F_max (20.5 kHz), thì cutoff_freq của toàn file phải được ghi nhận tối thiểu là F_max.
    frame_dt = (nperseg - noverlap) / sample_rate
    min_consec_frames = max(2, int(np.ceil(0.150 / frame_dt)))
    skip_boundary_frames = max(1, int(0.5 / frame_dt))  # Bỏ qua 0.5s đầu và 0.5s cuối file

    ultra_mask = (freqs >= 20_000.0) & (freqs <= min(21_800.0, nyquist))
    mid_mask = (freqs >= 1_000.0) & (freqs <= 8_000.0)

    has_local_peak_override = False
    longest_consec_ms = 0.0

    if (
        total_frames > (skip_boundary_frames * 2 + min_consec_frames)
        and ultra_mask.sum() > 0
        and mid_mask.sum() > 0
    ):
        ultra_energy_t = np.percentile(magnitude_db[ultra_mask, :], 80, axis=0)
        mid_energy_t = np.percentile(magnitude_db[mid_mask, :], 80, axis=0)

        # Năng lượng dải trung-cao (> -58 dBFS) xác nhận âm nhạc thực tế,
        # dải siêu cao (> -78 dBFS) xác nhận họa âm vươn tới 20-21.5 kHz
        is_musical_ultra = (ultra_energy_t > -78.0) & (mid_energy_t > -58.0)

        # Chỉ quét trong khoảng an toàn (bỏ qua mép đầu/cuối)
        valid_zone = is_musical_ultra[skip_boundary_frames : total_frames - skip_boundary_frames]

        current_run = 0
        max_run = 0
        for is_active in valid_zone:
            if is_active:
                current_run += 1
                if current_run > max_run:
                    max_run = current_run
            else:
                current_run = 0

        longest_consec_ms = max_run * frame_dt * 1000.0
        if max_run >= min_consec_frames:
            has_local_peak_override = True

    if has_local_peak_override and (cutoff_hz is None or cutoff_hz < 20_500.0):
        # Local peak override: Trần tần số thực tế đạt >= 20.5 kHz
        cutoff_hz = 20_500.0
        slope = None
        is_brickwall = False
        is_studio_filter = True
        encoder = "Studio Anti-Aliasing Filter (Redbook CD)"
        detail = (
            f"Quy tắc đỉnh cục bộ (Local Peak Override): Phát hiện cụm frame liên tiếp kéo dài "
            f"{longest_consec_ms:.0f}ms (>=150ms) có năng lượng âm nhạc hợp lệ vươn tới dải 20.5 kHz. "
            "Trần tần số thực tế của bản thu đạt chuẩn phòng thu (>=20.5 kHz), không bị cắt gọt lossy."
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

    # ── 3. Phép đo phân biệt Suy giảm tự nhiên vs Cắt cụt nhân tạo ──────────
    active_cutoff_ratio: Optional[float] = None
    cutoff_std_khz: Optional[float] = None
    pre_cutoff_energy_db: Optional[float] = None

    if cutoff_hz is not None:
        # Năng lượng sát mép cắt (Pre-cutoff energy) trong dải [cutoff_hz - 1.5 kHz, cutoff_hz]:
        pre_band = (freqs >= max(0.0, cutoff_hz - 1500.0)) & (freqs <= cutoff_hz)
        pre_cutoff_energy_db = float(np.mean(smoothed[pre_band])) if pre_band.sum() > 0 else -100.0

        # Các frame có âm lượng thực tế
        mid_band = (freqs >= 1000.0) & (freqs <= 8000.0)
        frame_mid_e = np.percentile(magnitude_db[mid_band, :], 85, axis=0) if mid_band.sum() > 0 else np.mean(magnitude_db, axis=0)
        audible_frames = frame_mid_e > -58.0
        if audible_frames.sum() < 5:
            audible_frames = np.ones(total_frames, dtype=bool)

        # Chỉ số 1: Mật độ khung thời gian chạm trần (active_cutoff_ratio)
        f_pre = max(0.0, cutoff_hz - 500.0)
        f_post = min(nyquist, cutoff_hz + 500.0)
        idx_pre = int(np.argmin(np.abs(freqs - f_pre)))
        idx_post = int(np.argmin(np.abs(freqs - f_post)))

        pre_e = magnitude_db[idx_pre, audible_frames]
        post_e = magnitude_db[idx_post, audible_frames]

        stopband_floor = float(np.percentile(post_e, 50))
        hits = (
            ((pre_e > -70.0) & (post_e < -88.0))
            | ((pre_e > -88.0) & ((pre_e - post_e) >= 15.0))
            | ((pre_e > (stopband_floor + 15.0)) & (post_e < -92.0))
        )
        active_cutoff_ratio = float(np.mean(hits)) if audible_frames.sum() > 0 else 0.0

        # Chỉ số 2: Độ lệch chuẩn của đỉnh tần số theo thời gian (cutoff_std_khz)
        detect_thresh = max(-92.0, min(-78.0, stopband_floor + 10.0))
        fmax_list = []
        audible_indices = np.where(audible_frames)[0]
        for t_idx in audible_indices:
            bins_above = np.where(magnitude_db[:, t_idx] > detect_thresh)[0]
            if len(bins_above) > 0:
                f_max_khz = float(freqs[bins_above[-1]] / 1000.0)
                if f_max_khz >= 8.0:
                    fmax_list.append(f_max_khz)

        if len(fmax_list) >= 5:
            # Lọc trung vị medfilt (kernel_size=3 hoặc 5) theo trục thời gian để loại bỏ các tia nhiễu xung đơn lẻ
            # (single-frame click/boundary spikes tại giây 10, 20, 30) làm lệch độ tản mác
            k_size = 5 if len(fmax_list) >= 5 else 3
            if k_size % 2 == 0:
                k_size -= 1
            fmax_arr = np.array(fmax_list, dtype=np.float64)
            filtered_fmax = signal.medfilt(fmax_arr, kernel_size=k_size)
            cutoff_std_khz = float(np.std(filtered_fmax))
        else:
            cutoff_std_khz = 1.2

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
            active_cutoff_ratio=round(active_cutoff_ratio, 3) if active_cutoff_ratio is not None else None,
            cutoff_std_khz=round(cutoff_std_khz, 3) if cutoff_std_khz is not None else None,
            pre_cutoff_energy_db=round(pre_cutoff_energy_db, 2) if pre_cutoff_energy_db is not None else None,
        ),
        freqs,
        smoothed,
    )
