"""
main.py — FastAPI application for TrueLossless Inspector.

Endpoints:
  GET  /api/health        → liveness check
  POST /api/analyze       → upload audio file & return full analysis JSON
"""
from __future__ import annotations

import logging
import os
import sys
import tempfile
import uuid
from pathlib import Path

# Ensure backend/ is on sys.path when running from that directory
sys.path.insert(0, str(Path(__file__).parent))

import numpy as np
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse

from config import MAX_UPLOAD_MB, SUPPORTED_EXTENSIONS, UPLOAD_DIR
from core.accuraterip import analyze_accuraterip
from core.ai_artifacts import analyze_ai_artifacts
from core.anti_spoof import analyze_anti_spoof
from core.bit_depth import analyze_bit_depth
from core.cover_art import extract_cover_and_tags
from core.ingestion import ingest
from core.natural_decay import analyze_natural_decay
from core.phase_coherence import analyze_phase_transient_coherence
from core.scorer import score_and_verdict
from core.spectrogram import render_spectrogram
from core.spectral_cutoff import analyze_spectral_cutoff, compute_stft_profile, _select_high_rms_frames
from core.ultrasonic import analyze_ultrasonic
from schemas import (
    AdvancedModulesSchema,
    AnalysisResponse,
    ErrorResponse,
    MetadataSchema,
    PillarsSchema,
    RolloffCurveSchema,
    UltrasonicSchema,
    VisualsSchema,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(name)s | %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Truefu Hires API",
    description="Analyze lossless audio files for authenticity.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure upload dir exists
Path(UPLOAD_DIR).mkdir(parents=True, exist_ok=True)


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "Truefu Hires"}


FIXTURES_DIR = Path(__file__).parent / "tests" / "fixtures"

DEMO_SAMPLES = {
    "authentic-24bit": {
        "id": "authentic-24bit",
        "title": "True 24-bit FLAC",
        "badge": "Authentic Studio Master",
        "filename": "true_24bit.flac",
        "type": "authentic",
    },
    "padded-24bit": {
        "id": "padded-24bit",
        "title": "Padded 24-bit (16-bit)",
        "badge": "Fake 24-bit (Zero-Padded)",
        "filename": "padded_24bit.flac",
        "type": "padded",
    },
    "fake-mp3": {
        "id": "fake-mp3",
        "title": "Fake MP3 128k Transcode",
        "badge": "Lossy MP3 Cutoff (~16-17 kHz)",
        "filename": "fake_mp3_128.flac",
        "type": "fake",
    },
    "spoofed-noise": {
        "id": "spoofed-noise",
        "title": "Spoofed White Noise",
        "badge": "Injected HF Noise Floor",
        "filename": "spoofed_noise.flac",
        "type": "spoofed",
    },
}


def _process_audio_file(file_path: Path, original_name: str) -> AnalysisResponse:
    """Core DSP pipeline execution for any local audio file."""
    # ── Phase 1: Ingestion ───────────────────────────────────────────────
    ingested     = ingest(str(file_path))
    raw_int32    = ingested["raw_int32"]
    float32_mono = ingested["float32_mono"]
    sample_rate  = ingested["sample_rate"]
    meta         = ingested["metadata"]
    is_dsd       = ingested["is_dsd"]
    probe        = ingested.get("probe", {})

    # Extract album cover art & track tags (title, artist, album)
    cover_art_b64, track_tags = extract_cover_and_tags(file_path, probe_dict=probe)

    # ── Phase 2: DSP Pillars ─────────────────────────────────────────────

    # Pillar 1 — Bit Depth
    bit_depth_result = analyze_bit_depth(raw_int32, meta["bits_per_raw_sample"])

    # Pillar 2 — Spectral Cutoff
    spectral_result, freqs, smoothed_profile = analyze_spectral_cutoff(
        float32_mono, sample_rate
    )

    # Full STFT magnitude matrix for anti-spoof
    from scipy import signal as sp_signal
    from config import STFT_NPERSEG_LOW, STFT_NOVERLAP_LOW
    _nperseg  = STFT_NPERSEG_LOW if sample_rate <= 48_000 else 8192
    _noverlap = STFT_NOVERLAP_LOW if sample_rate <= 48_000 else 4096
    _nperseg  = min(_nperseg, len(float32_mono))
    _noverlap = min(_noverlap, _nperseg - 1)
    _, _, Zxx = sp_signal.stft(
        float32_mono, fs=sample_rate,
        window="hann", nperseg=_nperseg, noverlap=_noverlap,
    )
    stft_mag_db = 20.0 * np.log10(np.maximum(np.abs(Zxx), 1e-7))

    # Pillar 3 — Anti-Spoof
    anti_spoof_result = analyze_anti_spoof(
        float32_mono, sample_rate, freqs, smoothed_profile, stft_mag_db
    )

    # Pillar 4 — Ultrasonic
    ultrasonic_result = analyze_ultrasonic(
        float32_mono, sample_rate, is_dsd, freqs, smoothed_profile
    )

    # Cross-validate bit depth against lossy spectral cutoff:
    # A true 24-bit studio recording does not brickwall at lossy codec limits (16-20 kHz).
    if spectral_result.is_brickwall and not spectral_result.is_studio_filter and bit_depth_result.declared >= 24 and not bit_depth_result.is_padded:
        bit_depth_result.suspicious_scaling = True
        cutoff_str = (
            f" at {spectral_result.detected_cutoff_hz/1000:.1f} kHz"
            if spectral_result.detected_cutoff_hz
            else ""
        )
        bit_depth_result.detail = (
            f"Declared {bit_depth_result.declared}-bit container, but audio has a brickwall cutoff{cutoff_str} "
            f"typical of lossy compression. Lower bits are synthetic dither / padding."
        )

    # Studio Anti-Aliasing Filter verification with authentic 16-bit/24-bit audio:
    fc = spectral_result.detected_cutoff_hz
    if fc is not None:
        slope_val = spectral_result.rolloff_slope_db_per_khz or 0.0
        is_authentic_bits = (
            not bit_depth_result.is_padded
            and not bit_depth_result.suspicious_scaling
            and bit_depth_result.effective >= 16
        )

        # 1. Studio Anti-Aliasing Filter (>= 21.0 kHz, near Nyquist boundary)
        is_studio_nyquist = (
            (21_000.0 <= fc <= 22_050.0)
            if sample_rate <= 44_100
            else (fc >= spectral_result.nyquist_hz * 0.95)
        )
        # 2. Studio Digital Master Filter (20.0 - 21.0 kHz with clean MDCT)
        is_digital_master = (
            fc >= 20_000.0
            and anti_spoof_result.spectral_holes_ratio < 0.04
            and not anti_spoof_result.holes_detected
        )

        if (is_studio_nyquist or is_digital_master) and is_authentic_bits:
            spectral_result.is_studio_filter = True
            spectral_result.is_brickwall = False
            if is_studio_nyquist:
                spectral_result.suspected_source_encoder = "Studio Anti-Aliasing Filter (Redbook CD)"
                spectral_result.detail = (
                    f"Studio anti-aliasing filter detected at {fc/1000:.2f} kHz "
                    f"(slope {slope_val:.1f} dB/kHz) near Nyquist boundary. "
                    "Preserves genuine Redbook CD audio bandwidth."
                )
            else:
                spectral_result.suspected_source_encoder = "Studio Digital Master Filter (Mora / Digital Master)"
                spectral_result.detail = (
                    f"Studio digital master filter detected at {fc/1000:.2f} kHz "
                    f"(slope {slope_val:.1f} dB/kHz). "
                    "Standard digital mastering filter for online distribution (Mora / Apple Music / CD). "
                    "Full 20 kHz original audio bandwidth preserved with clean MDCT."
                )

    # ── Phase 2.5: Advanced Detection Modules ────────────────────────────
    # Module A: Phase & Transient Coherence Check
    phase_coherence_result = analyze_phase_transient_coherence(
        float32_mono, sample_rate, freqs, stft_mag_db
    )

    # Module B: Spectral Rolloff Natural Decay Rate & Knee Discontinuity
    natural_decay_result = analyze_natural_decay(
        freqs, smoothed_profile, spectral_cutoff=spectral_result
    )

    # Module C: AccurateRip / CTDB CRC Checksum & Verification
    accuraterip_result = analyze_accuraterip(
        raw_int32, sample_rate, meta["bits_per_raw_sample"]
    )

    # Module D: AI / Neural Vocoder Artifacts (Spectral Phase Correlation & Pattern Repetition)
    ai_artifacts_result = analyze_ai_artifacts(
        float32_mono,
        sample_rate,
        freqs,
        stft_complex_zxx=Zxx,
        stft_magnitude_db=stft_mag_db,
        phase_coherence=phase_coherence_result,
        anti_spoof=anti_spoof_result,
    )

    advanced_result = AdvancedModulesSchema(
        phase_coherence=phase_coherence_result,
        natural_decay=natural_decay_result,
        accuraterip=accuraterip_result,
        ai_artifacts=ai_artifacts_result,
    )

    # ── Phase 3: Scoring ─────────────────────────────────────────────────
    verdict = score_and_verdict(
        bit_depth_result, spectral_result, anti_spoof_result, ultrasonic_result,
        advanced=advanced_result,
    )

    # ── Phase 4: Visuals ─────────────────────────────────────────────────
    MAX_CURVE_POINTS = 512
    step = max(1, len(freqs) // MAX_CURVE_POINTS)
    curve_freqs   = (freqs[::step] / 1000.0).tolist()
    curve_energy  = smoothed_profile[::step].tolist()

    spectrogram_b64 = render_spectrogram(
        float32_mono, sample_rate,
        detected_cutoff_hz=spectral_result.detected_cutoff_hz,
    )

    return AnalysisResponse(
        filename=original_name,
        verdict=verdict,
        metadata=MetadataSchema(
            codec=meta["codec"],
            sample_rate_hz=meta["sample_rate"],
            channels=meta["channels"],
            duration_sec=round(meta["duration"], 2),
            bitrate_kbps=meta["bitrate_kbps"],
            is_dsd=is_dsd,
            title=track_tags.get("title"),
            artist=track_tags.get("artist"),
            album=track_tags.get("album"),
            cover_art_base64=cover_art_b64,
        ),
        pillars=PillarsSchema(
            bit_depth=bit_depth_result,
            spectral_cutoff=spectral_result,
            anti_spoof=anti_spoof_result,
            ultrasonic=ultrasonic_result,
        ),
        advanced=advanced_result,
        visuals=VisualsSchema(
            rolloff_curve=RolloffCurveSchema(
                frequencies_khz=curve_freqs,
                energy_dbfs=curve_energy,
            ),
            spectrogram_base64=spectrogram_b64 or None,
        ),
    )


@app.get("/api/samples")
async def list_samples():
    """List preloaded demonstration audio files."""
    return [
        {
            "id": s["id"],
            "title": s["title"],
            "badge": s["badge"],
            "filename": s["filename"],
            "type": s["type"],
            "available": (FIXTURES_DIR / s["filename"]).exists(),
        }
        for s in DEMO_SAMPLES.values()
    ]


@app.post("/api/analyze-sample/{sample_id}", response_model=AnalysisResponse)
async def analyze_sample(sample_id: str):
    """Run full DSP pipeline on a preloaded demonstration fixture."""
    if sample_id not in DEMO_SAMPLES:
        raise HTTPException(status_code=404, detail="Sample not found")

    sample_info = DEMO_SAMPLES[sample_id]
    sample_path = FIXTURES_DIR / sample_info["filename"]

    if not sample_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Fixture '{sample_info['filename']}' not generated on server.",
        )

    try:
        return _process_audio_file(sample_path, sample_info["filename"])
    except Exception as exc:
        logger.exception("Sample analysis failed for %s: %s", sample_id, exc)
        raise HTTPException(status_code=500, detail=f"Analysis error: {exc}")


@app.get("/api/sample-audio/{sample_id}")
async def get_sample_audio(sample_id: str):
    """Serve sample audio file for direct in-browser playback."""
    if sample_id not in DEMO_SAMPLES:
        raise HTTPException(status_code=404, detail="Sample not found")

    sample_info = DEMO_SAMPLES[sample_id]
    sample_path = FIXTURES_DIR / sample_info["filename"]

    if not sample_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Fixture '{sample_info['filename']}' not found on server.",
        )

    ext = sample_path.suffix.lower()
    media_type = "audio/flac" if ext == ".flac" else "audio/wav" if ext == ".wav" else "audio/mpeg"
    return FileResponse(str(sample_path), media_type=media_type, filename=sample_info["filename"])


@app.post("/api/analyze", response_model=AnalysisResponse)
async def analyze_audio(file: UploadFile = File(...)):
    # ── Validate file extension ──────────────────────────────────────────────
    original_name = file.filename or "unknown"
    suffix        = Path(original_name).suffix.lower()

    if suffix not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type '{suffix}'. Supported: {sorted(SUPPORTED_EXTENSIONS)}",
        )

    # ── Stream upload directly to disk in 1MB chunks (memory-safe for 512MB RAM) ──
    tmp_path = Path(UPLOAD_DIR) / f"{uuid.uuid4().hex}{suffix}"
    total_bytes = 0
    max_bytes = MAX_UPLOAD_MB * 1024 * 1024
    CHUNK_SIZE = 1024 * 1024  # 1MB
    try:
        with open(tmp_path, "wb") as f_out:
            while chunk := await file.read(CHUNK_SIZE):
                total_bytes += len(chunk)
                if total_bytes > max_bytes:
                    raise HTTPException(
                        status_code=413,
                        detail=f"File exceeds {MAX_UPLOAD_MB} MB limit.",
                    )
                f_out.write(chunk)

        logger.info("Saved upload via streaming: %s (%d bytes)", tmp_path, total_bytes)
        result = _process_audio_file(tmp_path, original_name)
        return result

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Analysis failed for %s: %s", original_name, exc)
        raise HTTPException(status_code=500, detail=f"Analysis error: {exc}")
    finally:
        # Always clean up uploaded file & run garbage collection
        try:
            if tmp_path.exists():
                tmp_path.unlink()
        except OSError:
            pass
        import gc
        gc.collect()


# Mount static frontend if built (dist directory exists)
_frontend_dist = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if _frontend_dist.is_dir():
    from fastapi.staticfiles import StaticFiles
    app.mount("/", StaticFiles(directory=str(_frontend_dist), html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
