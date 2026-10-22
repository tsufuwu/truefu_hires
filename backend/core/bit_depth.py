"""
core/bit_depth.py — Pillar 1: True Bit-Depth & Wasted Bits Analyzer.

Key insight: soundfile left-shifts integer samples into int32.
  • True 16-bit → bits [16..31] set; bits [0..15] always zero  (Z_trail = 16)
  • True 24-bit → bits [8..31] set;  bits [0..7]  always zero  (Z_trail = 8)
  • True 32-bit → all bits used                                 (Z_trail = 0)

Algorithm:
  1. Bitwise-OR across |samples| to find the combined active bit pattern.
  2. Count trailing zero bits to determine how many LSB planes are empty.
  3. Per-frame LSB entropy check to catch software-gain-scaled 16-bit files.
"""
from __future__ import annotations

import logging
from typing import Any, Dict

import numpy as np

from config import LSB_ENTROPY_SAMPLE_LIMIT, MIN_DISTINCT_BOTTOM_BYTE_VALUES
from schemas import BitDepthSchema

logger = logging.getLogger(__name__)


def _count_trailing_zeros(n: int) -> int:
    """Return number of trailing zero bits in *n* (LSB → MSB)."""
    if n == 0:
        return 32
    count = 0
    while (n & 1) == 0:
        n >>= 1
        count += 1
    return count


def analyze_bit_depth(
    raw_int32: np.ndarray,
    declared_bits: int,
) -> BitDepthSchema:
    """
    Args:
        raw_int32:      (N, C) or (N,) soundfile int32 samples (left-shifted).
        declared_bits:  bits_per_raw_sample from ffprobe.

    Returns:
        BitDepthSchema with effective_bit_depth, wasted_bits, is_padded, etc.
    """
    if raw_int32.size == 0:
        return BitDepthSchema(
            declared=declared_bits,
            effective=declared_bits,
            wasted_bits=0,
            is_padded=False,
            suspicious_scaling=False,
            detail="No audio samples available for bit-depth analysis.",
        )

    flat = raw_int32.ravel()

    # ── Step 1: combined active-bit mask ────────────────────────────────────
    # Use only non-zero samples to avoid zeros padding the OR result
    nonzero = flat[flat != 0]
    if nonzero.size == 0:
        return BitDepthSchema(
            declared=declared_bits,
            effective=0,
            wasted_bits=32,
            is_padded=True,
            suspicious_scaling=False,
            detail="All samples are zero — silent or corrupt file.",
        )

    # np.bitwise_or.reduce requires signed int; use absolute values to get bit pattern
    abs_samples  = np.abs(nonzero).astype(np.int32)
    combined_bits = int(np.bitwise_or.reduce(abs_samples))

    z_trail      = _count_trailing_zeros(combined_bits)
    effective_bd = 32 - z_trail
    wasted_bits  = 32 - effective_bd - (32 - declared_bits)  # relative to declared container

    # Clamp wasted_bits to [0, declared_bits]
    wasted_bits = max(0, min(wasted_bits, declared_bits))

    # is_padded: declared 24-bit but effective ≤ 16-bit (wasted ≥ 8 LSB planes)
    is_padded = (declared_bits >= 24) and (effective_bd <= 16)

    # ── Step 2: LSB entropy check (anti-gain-scaling) ───────────────────────
    suspicious_scaling = False
    if declared_bits >= 24 and not is_padded:
        sample_pool = nonzero[:LSB_ENTROPY_SAMPLE_LIMIT]
        # Extract bits [8..15] (the lower byte of declared 24-bit data)
        bottom_byte_values = (sample_pool >> 8) & 0xFF
        distinct_count = len(np.unique(bottom_byte_values))
        if distinct_count < MIN_DISTINCT_BOTTOM_BYTE_VALUES:
            suspicious_scaling = True
            logger.debug(
                "Suspicious scaling: only %d distinct values in bottom byte.",
                distinct_count,
            )

    # ── Detail string ────────────────────────────────────────────────────────
    if is_padded:
        detail = (
            f"Bottom {32 - effective_bd} LSBs are permanently zero. "
            f"File is {effective_bd}-bit audio padded to {declared_bits}-bit container."
        )
    elif suspicious_scaling:
        detail = (
            f"Declared {declared_bits}-bit, effective {effective_bd}-bit. "
            "Bottom LSBs show fewer than 16 distinct values — possible gain-scaled 16-bit source."
        )
    elif effective_bd >= declared_bits - 1:
        detail = f"Full {declared_bits}-bit depth confirmed ({effective_bd} effective bits)."
    else:
        detail = f"Declared {declared_bits}-bit, effective {effective_bd}-bit ({wasted_bits} wasted bit-planes)."

    return BitDepthSchema(
        declared=declared_bits,
        effective=effective_bd,
        wasted_bits=wasted_bits,
        is_padded=is_padded,
        suspicious_scaling=suspicious_scaling,
        detail=detail,
    )
