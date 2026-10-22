"""
tests/generate_fixtures.py — Synthesize 4 short FLAC test fixtures.

Run from backend/ directory:
    python tests/generate_fixtures.py

Fixtures created in backend/tests/fixtures/:
  true_24bit.flac    — Genuine full-spectrum 24-bit/44.1 kHz signal to 22.05 kHz
  padded_24bit.flac  — 16-bit audio bit-shifted into 24-bit FLAC container
  fake_mp3_128.flac  — Signal encoded to 128 kbps MP3 via ffmpeg, decoded back
  spoofed_noise.flac — 128 kbps MP3 transcode + stationary white noise > 16 kHz
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.signal import chirp

FIXTURE_DIR = Path(__file__).parent / "fixtures"
FIXTURE_DIR.mkdir(exist_ok=True)

SAMPLE_RATE = 44_100
DURATION_SEC = 8
N = SAMPLE_RATE * DURATION_SEC


def make_broadband_signal(sr: int = SAMPLE_RATE, n: int = N) -> np.ndarray:
    """
    Synthesise a broadband musical-transient-like signal:
    Pink noise + multiple harmonic chirps from 20 Hz → 22 kHz.
    Returns float64 in [-0.5, 0.5].
    """
    rng  = np.random.default_rng(42)
    t    = np.arange(n) / sr

    # Pink noise via 1/f approximation
    white = rng.standard_normal(n)
    freqs_arr = np.fft.rfftfreq(n, 1 / sr)
    # Avoid divide-by-zero at DC
    pink_filter = np.where(freqs_arr > 0, 1.0 / np.sqrt(freqs_arr), 1.0)
    pink = np.fft.irfft(np.fft.rfft(white) * pink_filter, n=n)
    pink = pink / np.max(np.abs(pink)) * 0.3

    # Harmonic chirp bursts (musical transients)
    chirp1 = chirp(t, f0=100, f1=20_000, t1=DURATION_SEC, method="logarithmic")
    chirp2 = chirp(t, f0=200, f1=22_000, t1=DURATION_SEC, method="logarithmic")

    # Envelope to create attack/decay bursts (simulate percussive hits)
    env = np.zeros(n, dtype=float)
    for hit_sec in [0.5, 1.5, 2.5, 3.5, 4.5, 5.5, 6.5, 7.0]:
        hit_start = int(hit_sec * sr)
        env_len   = min(int(0.3 * sr), n - hit_start)
        if env_len > 0:
            envelope          = np.exp(-np.linspace(0, 10, env_len))
            env[hit_start: hit_start + env_len] += envelope

    combined = pink + 0.15 * chirp1 * env + 0.10 * chirp2 * env
    # Normalise to 0.5 peak
    combined = combined / np.max(np.abs(combined)) * 0.5
    return combined.astype(np.float64)


# ─────────────────────────────────────────────────────────────────────────────
# Fixture 1: true_24bit.flac
# ─────────────────────────────────────────────────────────────────────────────
def make_true_24bit():
    sig = make_broadband_signal()
    stereo = np.column_stack([sig, sig * 0.97])  # slight R channel difference
    out_path = FIXTURE_DIR / "true_24bit.flac"
    sf.write(str(out_path), stereo, SAMPLE_RATE, subtype="PCM_24")
    print(f"  Created: {out_path}")


# ─────────────────────────────────────────────────────────────────────────────
# Fixture 2: padded_24bit.flac (16-bit audio in 24-bit container)
# ─────────────────────────────────────────────────────────────────────────────
def make_padded_24bit():
    sig = make_broadband_signal()
    stereo = np.column_stack([sig, sig * 0.97])

    # Quantise to 16-bit integer range [-32768, 32767]
    int16 = (stereo * 32767).astype(np.int16)

    # Convert back to float64 via 16-bit scale (this is what 16-bit audio IS)
    float_16bit = int16.astype(np.float64) / 32768.0

    # Write as PCM_24 — soundfile stores at 24-bit precision,
    # so the lower 8 bits will be zero (the hallmark of padding)
    out_path = FIXTURE_DIR / "padded_24bit.flac"
    sf.write(str(out_path), float_16bit, SAMPLE_RATE, subtype="PCM_24")
    print(f"  Created: {out_path}")


# ─────────────────────────────────────────────────────────────────────────────
# Fixture 3: fake_mp3_128.flac (128 kbps MP3 → FLAC)
# ─────────────────────────────────────────────────────────────────────────────
def make_fake_mp3_128():
    sig = make_broadband_signal()
    stereo = np.column_stack([sig, sig * 0.97])

    # Write temporary WAV
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tf_wav:
        sf.write(tf_wav.name, stereo, SAMPLE_RATE, subtype="PCM_16")
        wav_path = tf_wav.name

    mp3_path  = wav_path.replace(".wav", ".mp3")
    flac_path = FIXTURE_DIR / "fake_mp3_128.flac"

    # Encode to 128 kbps MP3
    subprocess.run(
        ["ffmpeg", "-y", "-i", wav_path, "-b:a", "128k", "-codec:a", "libmp3lame", mp3_path],
        capture_output=True, check=True,
    )
    # Decode back to FLAC (the lossy→lossless transcode)
    subprocess.run(
        ["ffmpeg", "-y", "-i", mp3_path, "-c:a", "flac", str(flac_path)],
        capture_output=True, check=True,
    )
    Path(wav_path).unlink(missing_ok=True)
    Path(mp3_path).unlink(missing_ok=True)
    print(f"  Created: {flac_path}")


# ─────────────────────────────────────────────────────────────────────────────
# Fixture 4: spoofed_noise.flac (128 kbps MP3 + injected HF white noise)
# ─────────────────────────────────────────────────────────────────────────────
def make_spoofed_noise():
    sig = make_broadband_signal()
    stereo = np.column_stack([sig, sig * 0.97])

    # Step 1: write WAV, encode to 128k MP3, decode back
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tf_wav:
        sf.write(tf_wav.name, stereo, SAMPLE_RATE, subtype="PCM_16")
        wav_path = tf_wav.name

    mp3_path       = wav_path.replace(".wav", "_spoof.mp3")
    decoded_path   = wav_path.replace(".wav", "_decoded.wav")

    subprocess.run(
        ["ffmpeg", "-y", "-i", wav_path, "-b:a", "128k", "-codec:a", "libmp3lame", mp3_path],
        capture_output=True, check=True,
    )
    subprocess.run(
        ["ffmpeg", "-y", "-i", mp3_path, "-c:a", "pcm_f64le", decoded_path],
        capture_output=True, check=True,
    )

    decoded, _ = sf.read(decoded_path, dtype="float64", always_2d=True)

    # Apply a low-pass at 15.5 kHz to ensure the base signal is strictly
    # band-limited (as a real MP3-128k transcode would be)
    from scipy.signal import butter, sosfilt
    sos_lp  = butter(8, 15_500 / (SAMPLE_RATE / 2), btype="low", output="sos")
    decoded = sosfilt(sos_lp, decoded, axis=0)

    # Step 2: synthesise stationary white noise above 16 kHz at -55 dBFS
    rng       = np.random.default_rng(123)
    noise_len = decoded.shape[0]
    white     = rng.standard_normal((noise_len, 2)).astype(np.float64)

    # High-pass above 16 kHz using a simple IIR filter
    from scipy.signal import butter, sosfilt
    sos   = butter(8, 16_000 / (SAMPLE_RATE / 2), btype="high", output="sos")
    noise = sosfilt(sos, white, axis=0)
    # Scale to -75 dBFS amplitude
    amp   = 10 ** (-55 / 20)
    noise = noise / (np.max(np.abs(noise)) + 1e-9) * amp

    # Mix
    spoof = decoded + noise

    # Clip to valid float range
    spoof = np.clip(spoof, -1.0, 1.0)

    out_path = FIXTURE_DIR / "spoofed_noise.flac"
    sf.write(str(out_path), spoof.astype(np.float32), SAMPLE_RATE, subtype="PCM_24")

    # Cleanup
    for p in [wav_path, mp3_path, decoded_path]:
        Path(p).unlink(missing_ok=True)

    print(f"  Created: {out_path}")


# ─────────────────────────────────────────────────────────────────────────────
# Fixture 5: fake_mp3_24bit.flac (128 kbps MP3 upscaled to 24-bit FLAC container)
# ─────────────────────────────────────────────────────────────────────────────
def make_fake_mp3_24bit():
    sig = make_broadband_signal()
    stereo = np.column_stack([sig, sig * 0.97])

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tf_wav:
        sf.write(tf_wav.name, stereo, SAMPLE_RATE, subtype="PCM_16")
        wav_path = tf_wav.name

    mp3_path = wav_path.replace(".wav", "_temp24.mp3")
    decoded_path = wav_path.replace(".wav", "_decoded24.wav")
    flac_path = FIXTURE_DIR / "fake_mp3_24bit.flac"

    # Encode to 128 kbps MP3
    subprocess.run(
        ["ffmpeg", "-y", "-i", wav_path, "-b:a", "128k", "-codec:a", "libmp3lame", mp3_path],
        capture_output=True, check=True,
    )
    # Decode to 32-bit float audio (as standard audio editors do when importing MP3)
    subprocess.run(
        ["ffmpeg", "-y", "-i", mp3_path, "-c:a", "pcm_f32le", decoded_path],
        capture_output=True, check=True,
    )
    decoded, _ = sf.read(decoded_path, dtype="float32", always_2d=True)

    # Save as 24-bit FLAC (PCM_24 container with active float-quantized bits)
    sf.write(str(flac_path), decoded, SAMPLE_RATE, subtype="PCM_24")

    for p in [wav_path, mp3_path, decoded_path]:
        Path(p).unlink(missing_ok=True)
    print(f"  Created: {flac_path}")


# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("Generating test fixtures...")
    make_true_24bit()
    make_padded_24bit()
    make_fake_mp3_128()
    make_spoofed_noise()
    make_fake_mp3_24bit()
    print("Done. Fixtures in:", FIXTURE_DIR)
