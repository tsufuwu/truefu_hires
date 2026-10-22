"""
tests/test_advanced_modules.py — Unit tests for the 4 Advanced Detection Modules:
  Module A: Phase & Transient Coherence Check
  Module B: Spectral Rolloff Natural Decay Rate & Knee Discontinuity
  Module C: AccurateRip / CTDB CRC Checksum & Verification
  Module D: AI & Neural Vocoder Artifacts Detector
"""
import numpy as np
import pytest

from core.phase_coherence import analyze_phase_transient_coherence
from core.natural_decay import analyze_natural_decay
from core.accuraterip import compute_accuraterip_crc, analyze_accuraterip
from core.ai_artifacts import analyze_ai_artifacts


class TestModuleAPhaseCoherence:
    def test_genuine_transients_pass(self):
        sr = 44_100
        n = sr * 4
        t = np.arange(n) / sr
        freqs = np.linspace(0, 22_050, 2049)

        # Create simulated STFT with correlated transient bursts across mid and high bands
        n_frames = 100
        mag_db = np.full((len(freqs), n_frames), -90.0)

        # Mid band and HF band indices
        mid_idx = np.where((freqs >= 3000) & (freqs <= 7000))[0]
        hf_idx = np.where((freqs >= 16500) & (freqs <= 21000))[0]

        # Add transient bursts at frames 10, 30, 50, 70
        for f in [10, 30, 50, 70]:
            mag_db[mid_idx, f] = -20.0
            mag_db[hf_idx, f] = -35.0

        res = analyze_phase_transient_coherence(np.zeros(100), sr, freqs, mag_db)
        assert res.is_stealth_noise_layer is False
        assert res.status == "PASSED"

    def test_flat_artificial_noise_fails(self):
        sr = 44_100
        freqs = np.linspace(0, 22_050, 2049)
        n_frames = 100

        # Mid band has transients, but HF band is completely flat stationary noise (no transients)
        mag_db = np.full((len(freqs), n_frames), -90.0)
        mid_idx = np.where((freqs >= 3000) & (freqs <= 7000))[0]
        hf_idx = np.where((freqs >= 16500) & (freqs <= 21000))[0]

        for f in [10, 30, 50, 70]:
            mag_db[mid_idx, f] = -20.0

        # Flat noise in HF (variance near 0, no transient alignment)
        rng = np.random.default_rng(123)
        mag_db[hf_idx, :] = -60.0 + rng.normal(0, 0.3, size=(len(hf_idx), n_frames))

        res = analyze_phase_transient_coherence(np.zeros(100), sr, freqs, mag_db)
        assert res.is_stealth_noise_layer is True
        assert res.status == "FAILED"


class TestModuleBNaturalDecay:
    def test_natural_exponential_decay_passes(self):
        # Monotonically decaying profile from 10 kHz to 21 kHz: -4 dB/kHz
        freqs = np.linspace(0, 22_050, 2049)
        f_khz = freqs / 1000.0
        smooth_db = -30.0 - 3.5 * (f_khz - 10.0)

        res = analyze_natural_decay(freqs, smooth_db)
        assert res.violates_natural_decay is False
        assert res.status == "PASSED"

    def test_lossy_brickwall_flat_knee_fails(self):
        # Steep drop at 16 kHz followed by flat horizontal shelf
        freqs = np.linspace(0, 22_050, 2049)
        f_khz = freqs / 1000.0
        smooth_db = np.zeros_like(f_khz)

        # 10 to 15.5 kHz: gradual roll-off
        mask1 = f_khz < 15.5
        smooth_db[mask1] = -40.0 - 2.0 * (f_khz[mask1] - 10.0)

        # 15.5 to 16.5 kHz: steep drop
        mask2 = (f_khz >= 15.5) & (f_khz < 16.5)
        smooth_db[mask2] = -51.0 - 25.0 * (f_khz[mask2] - 15.5)

        # Above 16.5 kHz: flat noise shelf at -76 dBFS
        mask3 = f_khz >= 16.5
        smooth_db[mask3] = -76.0

        res = analyze_natural_decay(freqs, smooth_db)
        assert res.violates_natural_decay is True
        assert res.status == "FAILED"
        assert res.knee_frequency_khz is not None
        assert 15.0 <= res.knee_frequency_khz <= 17.0

    def test_mix_quirk_high_energy_passes(self):
        # Slope changes at 15.4 kHz from -9 dB/kHz to -1.8 dB/kHz (like J-Pop mix),
        # but energy remains high (~ -60 dBFS) extending to > 21 kHz with studio filter
        freqs = np.linspace(0, 22_050, 2049)
        f_khz = freqs / 1000.0
        smooth_db = np.zeros_like(f_khz)

        mask1 = f_khz < 15.4
        smooth_db[mask1] = -20.0 - 9.0 * (f_khz[mask1] - 10.0)

        mask2 = f_khz >= 15.4
        smooth_db[mask2] = -68.6 - 1.8 * (f_khz[mask2] - 15.4)

        from schemas import SpectralCutoffSchema
        dummy_spectral = SpectralCutoffSchema(
            detected_cutoff_hz=21_950.0,
            nyquist_hz=22_050.0,
            cutoff_margin_hz=100.0,
            rolloff_slope_db_per_khz=-450.0,
            is_brickwall=False,
            is_studio_filter=True,
            detail="Studio filter",
        )

        res = analyze_natural_decay(freqs, smooth_db, spectral_cutoff=dummy_spectral)
        assert res.violates_natural_decay is False
        assert res.status == "PASSED"
        assert res.knee_frequency_khz is not None
        assert "đặc thù bản phối" in res.detail


class TestModuleCAccurateRip:
    def test_accuraterip_crc_calculation(self):
        # Generate predictable 16-bit stereo PCM
        samples = np.array([
            [100, -100],
            [200, -200],
            [300, -300],
        ], dtype=np.int16)

        v1, v2, track_crc = compute_accuraterip_crc(samples)
        assert isinstance(v1, int)
        assert isinstance(v2, int)
        assert isinstance(track_crc, int)
        assert v1 != 0
        assert track_crc != 0

    def test_non_redbook_format_flagged(self):
        # 96 kHz / 24-bit audio
        raw = np.zeros((1000, 2), dtype=np.int32)
        res = analyze_accuraterip(raw, sample_rate=96_000, declared_bits=24, enable_network=False)
        assert res.db_status == "NON_REDBOOK"


class TestModuleDAiArtifacts:
    def test_clean_audio_no_ai_artifacts(self):
        # Clean sine tone in HF band
        sr = 44_100
        n = sr * 2
        t = np.arange(n) / sr
        mono = 0.5 * np.sin(2 * np.pi * 17_000 * t).astype(np.float32)
        freqs = np.linspace(0, 22_050, 1025)

        res = analyze_ai_artifacts(mono, sr, freqs)
        assert res.ai_artifacts_detected is False
        assert res.status == "PASSED"

    def test_distorted_guitars_with_transient_sync_passes(self):
        # Distorted electric guitar/synth track (like Kawaki wo Ameku)
        # Has broadband noise-like phase in HF (>16 kHz), but has high transient sync and clean MDCT
        from schemas import PhaseCoherenceSchema, AntiSpoofSchema

        sr = 44_100
        n = sr * 2
        np.random.seed(42)
        # Synthesize broadband signal with transients
        mono = (np.random.randn(n) * 0.1).astype(np.float32)
        freqs = np.linspace(0, 22_050, 1025)

        phase_coherence = PhaseCoherenceSchema(
            hf_time_variance_db=6.59,
            transient_concurrence_ratio=0.588,
            is_stealth_noise_layer=False,
            status="PASSED",
            detail="Good coherence",
        )
        anti_spoof = AntiSpoofSchema(
            spectral_holes_ratio=0.0013,
            holes_detected=False,
            hf_envelope_correlation=0.256,
            fake_noise_injected=False,
            detail="Clean",
        )

        res = analyze_ai_artifacts(
            mono, sr, freqs,
            phase_coherence=phase_coherence,
            anti_spoof=anti_spoof,
        )
        assert res.ai_artifacts_detected is False
        assert res.status == "PASSED"

