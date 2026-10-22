"""
core/ultrasonic.py — Pillar 4: Hi-Res & DSD Ultrasonic Authenticity Checker.

Checks:
  1. Upsampled-CD detection: brickwall drop ≥30 dB right at 22.05/24 kHz
     boundary in a file claiming ≥88.2 kHz sample rate.
  2. DSD ultrasonic correlation: for DSD files, the ultrasonic band (23–36 kHz)
     should be only Sigma-Delta noise (low correlation) in a transcoded file,
     but a genuine PCM→DSD or native DSD master will have predictable Σ-Δ
     modulation noise rising monotonically — not correlated with audio content.
"""
from __future__ import annotations

import logging
from typing import Optional, Tuple

import numpy as np
from scipy import signal as sp_signal
from scipy.signal import savgol_filter
from scipy.stats import pearsonr

from config import (
    DSD_AUDIBLE_HIGH_HZ,
    DSD_AUDIBLE_LOW_HZ,
    DSD_ULTRA_CORR_THRESH,
    DSD_ULTRA_HIGH_HZ,
    DSD_ULTRA_LOW_HZ,
    HIRES_SAMPLE_RATE_THRESHOLD,
    SAVGOL_POLY,
    SAVGOL_WINDOW,
    STFT_NPERSEG_HIGH,
    STFT_NOVERLAP_HIGH,
    UPSAMPLED_DROP_DB,
)
from schemas import UltrasonicSchema

logger = logging.getLogger(__name__)


def _band_env(mag_db: np.ndarray, freqs: np.ndarray, lo: float, hi: float) -> np.ndarray:
    mask = (freqs >= lo) & (freqs <= hi)
    if mask.sum() == 0:
        return np.zeros(mag_db.shape[1])
    return mag_db[mask, :].mean(axis=0)


def analyze_ultrasonic(
    float32_mono: np.ndarray,
    sample_rate: int,
    is_dsd: bool,
    freqs: Optional[np.ndarray] = None,
    smoothed_profile: Optional[np.ndarray] = None,
) -> UltrasonicSchema:
    """
    Evaluate Hi-Res / DSD ultrasonic authenticity.

    Args:
        float32_mono     : normalised mono audio
        sample_rate      : Hz (may be the converted DSD PCM rate)
        is_dsd           : True when source was .dsf / .dff
        freqs            : pre-computed STFT bins (Hz)
        smoothed_profile : pre-computed 95th-pct smoothed profile
    """
    nyquist = sample_rate / 2.0

    if sample_rate < HIRES_SAMPLE_RATE_THRESHOLD:
        return UltrasonicSchema(
            applicable=False,
            has_true_ultrasonic_transients=None,
            fake_hires_upsampled=False,
            ultrasonic_correlation=None,
            detail="Sample rate < 88.2 kHz — ultrasonic analysis not applicable.",
        )

    # ── Re-compute STFT at Hi-Res parameters if not provided ────────────────
    if freqs is None or smoothed_profile is None:
        nperseg  = STFT_NPERSEG_HIGH
        noverlap = STFT_NOVERLAP_HIGH
        nperseg  = min(nperseg, len(float32_mono))
        noverlap = min(noverlap, nperseg - 1)
        freqs_local, _, Zxx = sp_signal.stft(
            float32_mono, fs=sample_rate,
            window="hann", nperseg=nperseg, noverlap=noverlap,
        )
        mag_db = 20.0 * np.log10(np.maximum(np.abs(Zxx), 1e-7))
        smoothed_profile = savgol_filter(
            np.percentile(mag_db, 95, axis=1), SAVGOL_WINDOW, SAVGOL_POLY
        )
        freqs = freqs_local
    else:
        # Need the full matrix for correlation; recompute cheaply
        nperseg  = min(STFT_NPERSEG_HIGH, len(float32_mono))
        noverlap = min(STFT_NOVERLAP_HIGH, nperseg - 1)
        _, _, Zxx = sp_signal.stft(
            float32_mono, fs=sample_rate,
            window="hann", nperseg=nperseg, noverlap=noverlap,
        )
        mag_db = 20.0 * np.log10(np.maximum(np.abs(Zxx), 1e-7))

    # ════════════════════════════════════════════════════════════════════════
    # Check 1: Upsampled CD detection (brickwall at 22.05 / 24 kHz)
    # ════════════════════════════════════════════════════════════════════════
    fake_hires_upsampled = False

    boundary_map = {
        88_200:  22_050.0,
        176_400: 22_050.0,
        96_000:  24_000.0,
        192_000: 24_000.0,
    }
    boundary_hz = boundary_map.get(sample_rate)

    if boundary_hz and boundary_hz < nyquist:
        idx_boundary = np.searchsorted(freqs, boundary_hz)
        window_bins  = max(1, int(500 / (freqs[1] - freqs[0])))

        lo_idx = max(0, idx_boundary - window_bins)
        hi_idx = min(len(freqs) - 1, idx_boundary + window_bins)

        e_below = float(smoothed_profile[lo_idx])
        e_above = float(smoothed_profile[hi_idx])
        drop    = e_below - e_above

        if drop >= UPSAMPLED_DROP_DB:
            fake_hires_upsampled = True
            logger.debug(
                "Upsampled Hi-Res detected: %.1f dB drop at %.0f Hz",
                drop, boundary_hz,
            )

    # ════════════════════════════════════════════════════════════════════════
    # Check 2: DSD ultrasonic transient correlation
    # ════════════════════════════════════════════════════════════════════════
    ultrasonic_correlation: Optional[float] = None
    has_true_ultrasonic_transients: Optional[bool] = None

    ultra_max = min(DSD_ULTRA_HIGH_HZ, nyquist * 0.95)
    ultra_min = min(DSD_ULTRA_LOW_HZ, nyquist * 0.50)

    if ultra_min < ultra_max and ultra_min < nyquist:
        audible_env  = _band_env(mag_db, freqs, DSD_AUDIBLE_LOW_HZ, DSD_AUDIBLE_HIGH_HZ)
        ultrasonic_env = _band_env(mag_db, freqs, ultra_min, ultra_max)

        if np.std(audible_env) > 0 and np.std(ultrasonic_env) > 0:
            r, _ = pearsonr(audible_env, ultrasonic_env)
            ultrasonic_correlation = float(r)
            # For DSD files: genuine Σ-Δ noise should have VERY low correlation
            # For upsampled PCM posing as DSD: also low correlation (no real content)
            # We flag if correlation is suspiciously BELOW threshold as fake
            has_true_ultrasonic_transients = r >= DSD_ULTRA_CORR_THRESH

    # ── Detail string ────────────────────────────────────────────────────────
    parts = []
    if fake_hires_upsampled:
        parts.append(
            f"FAKE Hi-Res: brickwall cutoff detected at "
            f"{boundary_hz/1000:.2f} kHz — standard-res audio in Hi-Res container."
        )
    else:
        parts.append("No upsampled brickwall detected at expected CD/PCM boundaries.")

    if ultrasonic_correlation is not None:
        corr_str = f"r={ultrasonic_correlation:.3f}"
        if is_dsd:
            parts.append(
                f"DSD ultrasonic correlation ({corr_str}): "
                + ("Genuine Σ-Δ noise profile." if has_true_ultrasonic_transients
                   else "Suspiciously correlated — possible PCM→DSD transcode.")
            )
        else:
            parts.append(f"Ultrasonic band correlation {corr_str}.")

    return UltrasonicSchema(
        applicable=True,
        has_true_ultrasonic_transients=has_true_ultrasonic_transients,
        fake_hires_upsampled=fake_hires_upsampled,
        ultrasonic_correlation=(
            round(ultrasonic_correlation, 4) if ultrasonic_correlation is not None else None
        ),
        detail=" | ".join(parts) if parts else "Hi-Res analysis complete.",
    )
