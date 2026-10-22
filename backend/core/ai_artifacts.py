"""
core/ai_artifacts.py — Module D: AI & Neural Vocoder Artifacts Detector (Phase & Comb Repetition).

Principle:
  AI bandwidth extension models (e.g., AudioSR, HiFi-GAN, EnCodec neural vocoders)
  reconstruct lost high frequencies (16–24 kHz) through neural generation or transposed
  convolutions. These neural models inevitably leave mathematical fingerprints:
  1. Phase Jitter / Dispersion: Incoherent phase second-differences across time frames,
     exhibiting high circular entropy compared to genuine acoustic instruments.
  2. Spectral Comb Rippling & Patch Repetition: Transposed convolution checkerboard artifacts
     or sub-band harmonic replication create periodic ripple peaks detectable via
     spectral autocorrelation and cepstral analysis.
"""
from __future__ import annotations

import logging
from typing import Optional, Tuple
import numpy as np

from schemas import AiArtifactsSchema, PhaseCoherenceSchema, AntiSpoofSchema

logger = logging.getLogger(__name__)


def analyze_ai_artifacts(
    float32_mono: np.ndarray,
    sample_rate: int,
    freqs: np.ndarray,
    stft_complex_zxx: Optional[np.ndarray] = None,
    stft_magnitude_db: Optional[np.ndarray] = None,
    phase_coherence: Optional[PhaseCoherenceSchema] = None,
    anti_spoof: Optional[AntiSpoofSchema] = None,
) -> AiArtifactsSchema:
    """
    Detects neural vocoder phase jitter, periodic comb filtering ripples,
    and harmonic patch repetition in the high-frequency band (>15.5 kHz).
    """
    from scipy import signal as sp_signal

    nyquist = sample_rate / 2.0
    if nyquist < 17_000.0:
        return AiArtifactsSchema(
            phase_jitter_entropy=0.0,
            spectral_repetition_score=0.0,
            comb_ripple_db=0.0,
            ai_artifacts_detected=False,
            status="PASSED",
            detail="Tần số lấy mẫu không đủ để quét dải tạo tác AI (>16 kHz).",
        )

    # Compute STFT if needed
    if stft_complex_zxx is None:
        nperseg = 4096 if sample_rate <= 48_000 else 8192
        nperseg = min(nperseg, len(float32_mono))
        noverlap = min(nperseg // 2, nperseg - 1)
        freqs, _, Zxx = sp_signal.stft(
            float32_mono, fs=sample_rate,
            window="hann", nperseg=nperseg, noverlap=noverlap,
        )
    else:
        Zxx = stft_complex_zxx

    if stft_magnitude_db is None:
        mag_db = 20.0 * np.log10(np.maximum(np.abs(Zxx), 1e-7))
    else:
        mag_db = stft_magnitude_db

    hf_min = 15_500.0
    hf_max = min(22_000.0, nyquist)
    hf_mask = (freqs >= hf_min) & (freqs <= hf_max)

    if hf_mask.sum() < 10:
        return AiArtifactsSchema(
            phase_jitter_entropy=0.0,
            spectral_repetition_score=0.0,
            comb_ripple_db=0.0,
            ai_artifacts_detected=False,
            status="PASSED",
            detail="Dải tần số quá hẹp để phân tích tạo tác AI.",
        )

    # Check if HF band has sufficient energy
    hf_mag_sub = mag_db[hf_mask, :]
    hf_mean_energy = float(np.mean(hf_mag_sub))
    if hf_mean_energy < -85.0:
        return AiArtifactsSchema(
            phase_jitter_entropy=0.0,
            spectral_repetition_score=0.0,
            comb_ripple_db=0.0,
            ai_artifacts_detected=False,
            status="PASSED",
            detail="Dải tần >16 kHz không có tín hiệu tái tạo (năng lượng dưới -85 dBFS).",
        )

    # ── 1. Phase Jitter / Circular Dispersion Analysis ───────────────────────
    hf_zxx = Zxx[hf_mask, :]
    phases = np.angle(hf_zxx)  # (F, T)

    # Time-direction 2nd difference of phase: delta2_phi = phi(t) - 2*phi(t-1) + phi(t-2)
    if phases.shape[1] >= 4:
        d1 = np.diff(phases, axis=1)
        d1_wrapped = np.angle(np.exp(1j * d1))
        d2 = np.diff(d1_wrapped, axis=1)
        d2_wrapped = np.angle(np.exp(1j * d2))

        # Circular variance = 1 - |E[exp(j * d2)]|
        R = np.abs(np.mean(np.exp(1j * d2_wrapped)))
        phase_jitter = float(1.0 - R)
    else:
        phase_jitter = 0.0

    # ── 2. Spectral Autocorrelation & Comb Filter Ripple ─────────────────────
    hf_profile = np.percentile(hf_mag_sub, 80, axis=1)
    # Detrend
    hf_detrend = hf_profile - np.polyval(np.polyfit(np.arange(len(hf_profile)), hf_profile, 1), np.arange(len(hf_profile)))

    n_pts = len(hf_detrend)
    var = float(np.var(hf_detrend))
    delta_hz = float(freqs[1] - freqs[0]) if len(freqs) > 1 else 10.7
    max_repetition = 0.0
    comb_ripple = 0.0

    if var > 1e-4 and n_pts >= 32:
        autocorr = np.correlate(hf_detrend, hf_detrend, mode="full")
        autocorr = autocorr[n_pts - 1 :] / (var * n_pts)

        # Exclude the central lobe:
        # Must exit the main lobe shoulder and span at least 180 Hz lag
        min_lag = max(18, int(180.0 / delta_hz))
        diffs = np.diff(autocorr)
        valleys = np.where(diffs > 0)[0]
        if len(valleys) > 0:
            min_lag = max(min_lag, int(valleys[0]))

        max_lag = min(len(autocorr) - 2, n_pts // 2)
        if max_lag > min_lag + 4:
            from scipy.signal import find_peaks
            peaks, _ = find_peaks(autocorr[min_lag:max_lag], prominence=0.20)
            if len(peaks) > 0:
                max_repetition = float(np.max(autocorr[min_lag + peaks]))
            else:
                max_repetition = 0.0
        else:
            max_repetition = 0.0

        # Comb ripple amplitude:
        # High-frequency periodic oscillation around the smoothed profile (Savitzky-Golay)
        from scipy.signal import savgol_filter
        win = min(31, n_pts if n_pts % 2 != 0 else n_pts - 1)
        if win >= 7:
            hf_smooth = savgol_filter(hf_profile, window_length=win, polyorder=2)
            hf_oscillation = hf_profile - hf_smooth
            comb_ripple = float(np.percentile(hf_oscillation, 98) - np.percentile(hf_oscillation, 2))
        else:
            comb_ripple = 0.0

    # ── 3. Cross-Validation with Acoustic Transients & MDCT Cleanliness ──────
    # Distorted electric guitars, synths, and heavy drums naturally have phase dispersion,
    # but their transients are tightly phase-locked with the mid-band rhythm section.
    transient_sync = bool(phase_coherence and phase_coherence.transient_concurrence_ratio >= 0.35)
    clean_mdct = bool(anti_spoof and anti_spoof.spectral_holes_ratio < 0.04 and not anti_spoof.holes_detected)
    is_genuine_acoustic = transient_sync and clean_mdct

    # Decision criteria for AI neural vocoder artifacts:
    # Requires genuine comb repetition peaks AND high ripple amplitude,
    # and must NOT be an authentic acoustic track with synchronized rhythm transients.
    ai_detected = bool(
        not is_genuine_acoustic
        and (
            (phase_jitter > 0.94 and max_repetition > 0.65 and comb_ripple > 7.0)
            or (max_repetition > 0.80 and comb_ripple > 9.0)
        )
    )

    if ai_detected:
        status = "FAILED"
        detail = (
            f"CẢNH BÁO: Phát hiện tạo tác AI / Neural Vocoder! "
            f"Độ tán xạ pha dải cao {phase_jitter:.3f} (hỗn loạn cao) cùng chỉ số lặp cấu trúc mẫu {max_repetition:.2f} "
            f"(biên độ gợn sóng comb {comb_ripple:.1f} dB). Đây là dấu vết thuật toán AI/AudioSR vẽ bù dải cao giả lập."
        )
    else:
        status = "PASSED"
        detail = (
            f"Không phát hiện tạo tác AI (độ ổn định pha {1.0 - phase_jitter:.2f}, "
            f"chỉ số lặp cấu trúc mẫu {max_repetition:.2f} bình thường, biên độ gợn sóng {comb_ripple:.1f} dB). "
            "Dải tần tự nhiên không có dấu hiệu tái tạo mạng nơ-ron."
        )

    return AiArtifactsSchema(
        phase_jitter_entropy=round(float(phase_jitter), 3),
        spectral_repetition_score=round(float(max_repetition), 3),
        comb_ripple_db=round(float(comb_ripple), 2),
        ai_artifacts_detected=ai_detected,
        status=status,
        detail=detail,
    )
