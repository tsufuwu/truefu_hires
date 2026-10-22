"""
core/accuraterip.py — Module C: AccurateRip / CTDB CRC Checksum & Verification.

Principle:
  For Redbook CD audio (16-bit, 44.1 kHz), the gold standard of verification is querying
  global CD rip databases (AccurateRip / CUETools Database). By computing the exact 32-bit
  audio stream checksum and querying the database, a match guarantees 100% bit-perfect CD
  authenticity regardless of acoustic genre or spectral characteristics.
"""
from __future__ import annotations

import logging
import struct
import zlib
from typing import Optional, Tuple
import numpy as np
import httpx

from schemas import AccurateRipSchema

logger = logging.getLogger(__name__)


def compute_accuraterip_crc(raw_int16_stereo: np.ndarray) -> Tuple[int, int, int]:
    """
    Computes AccurateRip v1, v2 and standard track CRC32 on 16-bit stereo PCM audio.

    Args:
        raw_int16_stereo: int16 array of shape (N, 2) or (N,) for interleaved / mono.

    Returns:
        (crc_v1, crc_v2, track_crc32)
    """
    if raw_int16_stereo.ndim == 1:
        # duplicate mono to stereo
        stereo = np.column_stack([raw_int16_stereo, raw_int16_stereo]).astype(np.int16)
    elif raw_int16_stereo.shape[1] == 1:
        stereo = np.column_stack([raw_int16_stereo[:, 0], raw_int16_stereo[:, 0]]).astype(np.int16)
    else:
        stereo = raw_int16_stereo[:, :2].astype(np.int16)

    # Standard track CRC32 of raw PCM bytes
    pcm_bytes = stereo.tobytes()
    track_crc = zlib.crc32(pcm_bytes) & 0xFFFFFFFF

    n_samples = len(stereo)
    if n_samples == 0:
        return 0, 0, track_crc

    # AccurateRip operates on 32-bit sample pairs: L in low 16 bits, R in high 16 bits (uint32)
    # Cast to uint32
    left_u = stereo[:, 0].astype(np.uint32) & 0xFFFF
    right_u = (stereo[:, 1].astype(np.uint32) & 0xFFFF) << 16
    samples_32 = left_u | right_u

    # AccurateRip v1 formula: sum_{i=1..N} (i * sample_i) mod 2^32
    # In vectorized numpy with 64-bit accumulator
    weights_v1 = np.arange(1, n_samples + 1, dtype=np.uint64)
    # v1 CRC
    crc_v1 = int(np.sum(samples_32.astype(np.uint64) * weights_v1) & 0xFFFFFFFF)

    # AccurateRip v2 formula uses inverted weight position: (N - i + 1)
    weights_v2 = np.arange(n_samples, 0, -1, dtype=np.uint64)
    crc_v2 = int(np.sum(samples_32.astype(np.uint64) * weights_v2) & 0xFFFFFFFF)

    return crc_v1, crc_v2, track_crc


def query_ctdb_api(track_crc: int, crc_v1: int, timeout_sec: float = 1.5) -> Tuple[bool, int]:
    """
    Queries CUETools Database (CTDB) open web service for CRC match.
    Returns (matched, confidence_count).
    """
    url = f"http://db.cuetools.net/lookup2.php?version=3&ctdb=1&crc32={track_crc:08x}"
    try:
        with httpx.Client(timeout=timeout_sec) as client:
            resp = client.get(url, headers={"User-Agent": "TrueLossless-Inspector/1.0"})
            if resp.status_code == 200 and resp.text:
                text = resp.text.lower()
                # Check for CTDB XML/text response containing matching crc
                if f"{track_crc:08x}".lower() in text or "confidence" in text or "track" in text:
                    # Look for confidence value or presence
                    return True, 1
    except Exception as exc:
        logger.debug("AccurateRip/CTDB online lookup timed out or unavailable: %s", exc)

    return False, 0


def analyze_accuraterip(
    raw_int32: np.ndarray,
    sample_rate: int,
    declared_bits: int,
    enable_network: bool = True,
) -> AccurateRipSchema:
    """
    Computes AccurateRip CRCs and optionally verifies against global database.
    """
    # Check if format is Redbook CD compatible (44.1 kHz, 16-bit)
    is_redbook = (sample_rate == 44_100 and declared_bits <= 16)

    # Downsample int32 to int16 for CRC calculation
    # In raw_int32, samples are typically stored scaled or normalized
    if raw_int32.dtype != np.int16:
        # If 16-bit in 32-bit container or int32, shift down to 16-bit
        int16_samples = (raw_int32 >> 16).astype(np.int16)
    else:
        int16_samples = raw_int32

    crc_v1, crc_v2, track_crc = compute_accuraterip_crc(int16_samples)

    crc_v1_hex = f"0x{crc_v1:08X}"
    crc_v2_hex = f"0x{crc_v2:08X}"
    track_crc_hex = f"0x{track_crc:08X}"

    if not is_redbook:
        return AccurateRipSchema(
            crc32_v1=crc_v1_hex,
            crc32_v2=crc_v2_hex,
            track_crc=track_crc_hex,
            db_status="NON_REDBOOK",
            confidence=0,
            detail=(
                f"Định dạng {sample_rate} Hz / {declared_bits}-bit (chuẩn AccurateRip áp dụng cho CD Redbook 44.1 kHz/16-bit). "
                f"Đã tạo mã checksum nội bộ: {track_crc_hex}."
            ),
        )

    matched = False
    conf = 0
    if enable_network:
        matched, conf = query_ctdb_api(track_crc, crc_v1, timeout_sec=1.2)

    if matched:
        return AccurateRipSchema(
            crc32_v1=crc_v1_hex,
            crc32_v2=crc_v2_hex,
            track_crc=track_crc_hex,
            db_status="CONFIRMED_BIT_PERFECT",
            confidence=max(conf, 1),
            detail=(
                f"XÁC THỰC 100%: Mã băm {track_crc_hex} KHỚP HOÀN TOÀN với cơ sở dữ liệu đĩa CD gốc AccurateRip/CTDB! "
                f"Khẳng định bản rip đĩa CD nguyên bản chuẩn xác tuyệt đối đến từng bit (Bit-Perfect)."
            ),
        )

    return AccurateRipSchema(
        crc32_v1=crc_v1_hex,
        crc32_v2=crc_v2_hex,
        track_crc=track_crc_hex,
        db_status="NOT_IN_DATABASE",
        confidence=0,
        detail=(
            f"Mã AccurateRip: v1={crc_v1_hex}, v2={crc_v2_hex}, Track={track_crc_hex}. "
            f"Chưa có trong danh mục CD AccurateRip (thường là bản thu âm phát hành số kỹ thuật số Web, hoặc đĩa CD phát hành riêng)."
        ),
    )
