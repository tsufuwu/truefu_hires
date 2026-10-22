"""
core/phase_coherence.py — Module A: Phase & Transient Coherence Check.

Principle:
  Real musical instruments (piano hammer, cymbals, snare drum, acoustic transients)
  generate high-frequency energy that strictly co-occurs with mid-range transients in time.
  In contrast, artificial noise or lossy encoder residual noise floors exhibit a flat,
  stationary distribution across time ("phẳng lì như mặt hồ") with near-zero temporal
  variance and missing transient spikes in the upper spectrum (>16 kHz).
"""
from __future__ import annotations

import logging
from typing import Optional, Tuple
import numpy as np

from schemas import PhaseCoherenceSchema

logger = logging.getLogger(__name__)


def analyze_phase_transient_coherence(
    float32_mono: np.ndarray,
    sample_rate: int,
    freqs: np.ndarray,
    stft_magnitude_db: np.ndarray,
) -> PhaseCoherenceSchema:
    """
    Examines the time-domain variance and transient concurrence of the HF band (>16 kHz).
    """
    nyquist = sample_rate / 2.0
    hf_min_hz = 16_000.0
    hf_max_hz = min(22_050.0, nyquist)
    mid_min_hz = 2_500.0
    mid_max_hz = 8_000.0

    # If Nyquist <= 16 kHz (e.g., 32 kHz sample rate), cannot check HF band
    if nyquist <= hf_min_hz:
        return PhaseCoherenceSchema(
            hf_time_variance_db=0.0,
            transient_concurrence_ratio=1.0,
            is_stealth_noise_layer=False,
            status="PASSED",
            detail="Tần số lấy mẫu quá thấp (Nyquist <= 16 kHz), bỏ qua kiểm tra dải cao.",
        )

    hf_mask = (freqs >= hf_min_hz) & (freqs <= hf_max_hz)
    mid_mask = (freqs >= mid_min_hz) & (freqs <= mid_max_hz)

    if hf_mask.sum() == 0 or mid_mask.sum() == 0:
        return PhaseCoherenceSchema(
            hf_time_variance_db=0.0,
            transient_concurrence_ratio=1.0,
            is_stealth_noise_layer=False,
            status="PASSED",
            detail="Không đủ dải tần để phân tích pha và tính đồng nhất.",
        )

    # High frequency energy envelope across time (90th percentile of active bins)
    hf_sub = stft_magnitude_db[hf_mask, :]
    mid_sub = stft_magnitude_db[mid_mask, :]

    hf_env = np.percentile(hf_sub, 90, axis=0)
    mid_env = np.percentile(mid_sub, 90, axis=0)

    hf_max_db = float(hf_sub.max())
    hf_mean_db = float(hf_env.mean())
    hf_std_db = float(np.std(hf_env))

    # If HF band has practically no energy, it's cut off, not an injected stealth noise layer
    if hf_max_db < -82.0 or hf_mean_db < -95.0:
        return PhaseCoherenceSchema(
            hf_time_variance_db=round(hf_std_db, 2),
            transient_concurrence_ratio=0.0,
            is_stealth_noise_layer=False,
            status="NO_HF_ENERGY",
            detail="Dải tần >16 kHz không có năng lượng đáng kể (đã bị vách cắt triệt tiêu hoàn toàn).",
        )

    # Compute transient onsets (positive half-wave rectified 1st derivative)
    mid_diff = np.maximum(0.0, np.diff(mid_env))
    hf_diff = np.maximum(0.0, np.diff(hf_env))

    # Identify significant transient frames in mid band
    mid_thresh = np.percentile(mid_diff, 85)
    hf_thresh = np.percentile(hf_diff, 85)

    mid_transients = mid_diff >= max(mid_thresh, 1.5)
    hf_transients = hf_diff >= max(hf_thresh, 1.0)

    if hf_transients.sum() == 0:
        concurrence_ratio = 0.0
    else:
        # Check alignment within +/- 1 frame
        aligned = 0
        hf_idx = np.where(hf_transients)[0]
        n_frames = len(mid_transients)
        for idx in hf_idx:
            start = max(0, idx - 1)
            end = min(n_frames, idx + 2)
            if np.any(mid_transients[start:end]):
                aligned += 1
        concurrence_ratio = float(aligned / len(hf_idx))

    # Detection logic:
    # A genuine track with HF energy will have musical transient alignment with mid band (concurrence_ratio >= 0.30)
    # or dynamic variance across time frames.
    # An artificial flat lake has stationary energy across time (low variance) AND lacks transient concurrence.
    is_flat_lake = (hf_std_db < 2.5 and hf_mean_db > -85.0 and concurrence_ratio < 0.25)
    is_disconnected_transients = (concurrence_ratio < 0.20 and hf_mean_db > -75.0 and hf_std_db < 3.5)

    is_stealth_noise = bool(is_flat_lake or is_disconnected_transients)

    if is_stealth_noise:
        status = "FAILED"
        if is_flat_lake:
            detail = (
                f"CẢNH BÁO: Dải >16 kHz có năng lượng ({hf_mean_db:.1f} dBFS) nhưng phẳng lì "
                f"như mặt hồ (độ biến thiên thời gian σ={hf_std_db:.2f} dB, thiếu vệt xung đồng bộ). "
                f"Không xuất hiện các vệt vách xung (transient spikes) của nhạc cụ thật — dấu vết dải nhiễu nhân tạo/dither độn."
            )
        else:
            detail = (
                f"CẢNH BÁO: Vệt xung dải cao (>16 kHz) mất đồng bộ với dải trung (tỷ lệ đồng nhất chỉ {concurrence_ratio*100:.1f}%). "
                f"Năng lượng dải cao không bắt nguồn từ nhạc cụ thật mà là tạp âm chèn thêm."
            )
    else:
        status = "PASSED"
        detail = (
            f"Độ phân bố pha và tính đồng nhất tốt (độ biến thiên σ={hf_std_db:.2f} dB, "
            f"tỷ lệ đồng bộ vệt xung {concurrence_ratio*100:.1f}%). Xác nhận có vệt xung nhạc cụ thật đồng thời giữa dải trung và dải cao."
        )

    return PhaseCoherenceSchema(
        hf_time_variance_db=round(hf_std_db, 2),
        transient_concurrence_ratio=round(concurrence_ratio, 3),
        is_stealth_noise_layer=is_stealth_noise,
        status=status,
        detail=detail,
    )
