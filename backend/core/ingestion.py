"""
core/ingestion.py — Audio metadata extraction + memory-safe PCM loading.

Design decisions:
- soundfile reads raw int32 samples (left-shifted) to preserve LSB information
  for bit-depth analysis BEFORE any normalization.
- Long files are sampled at 20%, 50%, and 80% positions rather than loaded
  in full, capping RAM usage to ~3 × 10 s × 2 ch × 48000 Hz × 4 B ≈ 115 MB.
- DSD (.dsf / .dff) files are piped through ffmpeg → s32le PCM at 88.2 kHz.
"""
from __future__ import annotations

import io
import json
import logging
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import numpy as np
import soundfile as sf

from config import (
    CHUNK_DURATION_SEC,
    DSD_EXTENSIONS,
    DSD_PCM_SAMPLE_RATE,
    DSD_SLICE_SECONDS,
    MAX_ANALYSIS_SECONDS,
    SAMPLE_POSITIONS,
)

logger = logging.getLogger(__name__)


# ────────────────────────────────────────────────────────────────────────────
# 1.  ffprobe metadata
# ────────────────────────────────────────────────────────────────────────────

def run_ffprobe(filepath: str) -> Dict[str, Any]:
    """Return parsed ffprobe JSON for *filepath*."""
    cmd = [
        "ffprobe", "-v", "quiet",
        "-print_format", "json",
        "-show_format", "-show_streams",
        filepath,
    ]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
        if not result.stdout:
            return {}
        return json.loads(result.stdout)
    except Exception as exc:
        logger.warning("ffprobe failed for %s: %s", filepath, exc)
        return {}


def parse_metadata(probe: Dict[str, Any]) -> Dict[str, Any]:
    """Extract the relevant fields from an ffprobe dict."""
    stream = next(
        (s for s in probe.get("streams", []) if s.get("codec_type") == "audio"),
        {},
    )
    fmt = probe.get("format", {})

    sample_rate  = int(stream.get("sample_rate", 44100))
    channels     = int(stream.get("channels", 2))
    duration     = float(fmt.get("duration") or stream.get("duration") or 0.0)
    bit_rate     = float(fmt.get("bit_rate") or stream.get("bit_rate") or 0.0) / 1000.0
    codec        = stream.get("codec_name", "unknown").upper()
    bits_per_raw = int(
        stream.get("bits_per_raw_sample")
        or stream.get("bits_per_sample")
        or 16
    )

    return {
        "codec": codec,
        "sample_rate": sample_rate,
        "channels": channels,
        "duration": duration,
        "bitrate_kbps": round(bit_rate, 1) if bit_rate else None,
        "bits_per_raw_sample": bits_per_raw,
    }


# ────────────────────────────────────────────────────────────────────────────
# 2.  DSD → PCM via ffmpeg pipe
# ────────────────────────────────────────────────────────────────────────────

def load_dsd_as_pcm(
    filepath: str,
    duration_total: float,
) -> Tuple[np.ndarray, np.ndarray, int]:
    """
    Convert up to DSD_SLICE_SECONDS from the middle of a DSD file to PCM.
    Returns (raw_int32, float32_mono, sample_rate).
    """
    start_sec = max(0.0, duration_total / 2.0 - DSD_SLICE_SECONDS / 2.0)

    cmd = [
        "ffmpeg", "-v", "quiet",
        "-ss", str(start_sec),
        "-t",  str(DSD_SLICE_SECONDS),
        "-i",  filepath,
        "-f",  "s32le",
        "-acodec", "pcm_s32le",
        "-ar", str(DSD_PCM_SAMPLE_RATE),
        "-ac", "2",
        "pipe:1",
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, timeout=120)
        raw_bytes = result.stdout
    except subprocess.TimeoutExpired:
        logger.error("ffmpeg DSD conversion timed out for %s", filepath)
        raw_bytes = b""

    if not raw_bytes:
        return np.array([], dtype=np.int32), np.array([], dtype=np.float32), DSD_PCM_SAMPLE_RATE

    # Interleaved stereo s32le
    raw_int32 = np.frombuffer(raw_bytes, dtype=np.int32)
    # Reshape to (samples, 2) for stereo
    if raw_int32.size % 2 == 0:
        raw_int32 = raw_int32.reshape(-1, 2)
    else:
        raw_int32 = raw_int32[:-1].reshape(-1, 2)

    float32 = raw_int32.astype(np.float32) / 2**31
    mono     = float32.mean(axis=1)
    return raw_int32, mono, DSD_PCM_SAMPLE_RATE


# ────────────────────────────────────────────────────────────────────────────
# 3.  Standard PCM loader (soundfile, chunked)
# ────────────────────────────────────────────────────────────────────────────

def load_pcm_segments(
    filepath: str,
    sample_rate: int,
    duration: float,
    channels: int,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Load up to MAX_ANALYSIS_SECONDS of audio in CHUNK_DURATION_SEC chunks
    sampled from SAMPLE_POSITIONS within the track.

    Returns:
        raw_int32  : (N, channels) int32  — left-shifted soundfile integers
        float32    : (N,)          float32 — normalised [-1, 1] mono
    """
    chunk_frames = int(CHUNK_DURATION_SEC * sample_rate)
    raw_chunks: list[np.ndarray] = []

    with sf.SoundFile(filepath) as f:
        total_frames = len(f)
        # Always use frame count to compute reliable duration
        calc_duration = total_frames / sample_rate if sample_rate > 0 else duration

        if 0 < calc_duration <= CHUNK_DURATION_SEC * 3:
            # Short file (under 30s): load cleanly
            f.seek(0)
            data = f.read(dtype="int32", always_2d=True)
            raw_chunks.append(data)
        else:
            # Files over 30s: sample 3 representative 10-s segments (20%, 50%, 80%)
            for pos in SAMPLE_POSITIONS:
                start_frame = int(pos * total_frames)
                start_frame = max(0, min(start_frame, total_frames - chunk_frames))
                f.seek(start_frame)
                data = f.read(frames=chunk_frames, dtype="int32", always_2d=True)
                if data.size:
                    raw_chunks.append(data)

    if not raw_chunks:
        return np.array([], dtype=np.int32), np.array([], dtype=np.float32)

    raw_int32 = np.concatenate(raw_chunks, axis=0)          # (N, C) int32
    # Memory-safe mono conversion: avoids duplicating massive (N, C) float32 array
    if raw_int32.ndim > 1 and raw_int32.shape[1] > 1:
        mono = raw_int32.mean(axis=1).astype(np.float32) / (2**31)
    else:
        mono = raw_int32.flatten().astype(np.float32) / (2**31)
    return raw_int32, mono


# ────────────────────────────────────────────────────────────────────────────
# 4.  Public entry point
# ────────────────────────────────────────────────────────────────────────────

def ingest(filepath: str) -> Dict[str, Any]:
    """
    Full ingestion pipeline.

    Returns a dict with keys:
        metadata        : dict from parse_metadata()
        raw_int32       : np.ndarray (N, C) int32
        float32_mono    : np.ndarray (N,)  float32
        sample_rate     : int
        is_dsd          : bool
    """
    path = Path(filepath)
    ext  = path.suffix.lower()
    is_dsd = ext in DSD_EXTENSIONS

    probe    = run_ffprobe(filepath)
    metadata = parse_metadata(probe)

    if is_dsd:
        raw_int32, float32_mono, sr = load_dsd_as_pcm(
            filepath, metadata["duration"]
        )
        metadata["sample_rate"] = sr
        metadata["bits_per_raw_sample"] = 24
    else:
        raw_int32, float32_mono = load_pcm_segments(
            filepath,
            metadata["sample_rate"],
            metadata["duration"],
            metadata["channels"],
        )
        sr = metadata["sample_rate"]

    return {
        "metadata": metadata,
        "raw_int32": raw_int32,
        "float32_mono": float32_mono,
        "sample_rate": sr,
        "is_dsd": is_dsd,
        "probe": probe,
    }
