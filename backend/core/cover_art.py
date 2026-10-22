"""
core/cover_art.py — Extract embedded album art & track tags from FLAC and audio files.

Supports:
1. Ultra-fast native FLAC binary parser (reads PICTURE block 6 & VORBIS_COMMENT block 4)
2. FFmpeg / FFprobe fallback for non-FLAC containers (MP3 ID3 APIC, M4A/ALAC, AIFF, WAV, DSD)
3. PIL-based thumbnail optimization (caps oversized images to max 800x800 for crisp, lightweight payloads)
"""
from __future__ import annotations

import base64
import io
import json
import logging
import struct
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

# Try to import PIL for image optimization/resizing
try:
    from PIL import Image
    _HAS_PIL = True
except ImportError:
    _HAS_PIL = False


def _detect_mime_from_magic(data: bytes) -> str:
    """Guess image MIME type from initial header bytes."""
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"RIFF") and len(data) >= 12 and data[8:12] == b"WEBP":
        return "image/webp"
    if data.startswith(b"GIF87a") or data.startswith(b"GIF89a"):
        return "image/gif"
    if data.startswith(b"BM"):
        return "image/bmp"
    return "image/jpeg"


def _optimize_and_encode_image(raw_bytes: bytes, raw_mime: str = "") -> Optional[str]:
    """Convert raw image bytes to an optimized Base64 data URL."""
    if not raw_bytes:
        return None

    mime = raw_mime.strip().lower() if raw_mime else ""
    if not mime or mime == "-->":
        mime = _detect_mime_from_magic(raw_bytes)

    # If PIL is available, optimize to keep JSON response snappy
    if _HAS_PIL:
        try:
            with Image.open(io.BytesIO(raw_bytes)) as img:
                # Convert RGBA to RGB if saving to JPEG
                target_format = "JPEG"
                target_mime = "image/jpeg"
                if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
                    target_format = "PNG"
                    target_mime = "image/png"

                max_dim = 800
                if img.width > max_dim or img.height > max_dim:
                    img.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)

                out_buf = io.BytesIO()
                if target_format == "JPEG":
                    if img.mode != "RGB":
                        img = img.convert("RGB")
                    img.save(out_buf, format="JPEG", quality=88, optimize=True)
                else:
                    img.save(out_buf, format="PNG", optimize=True)

                out_bytes = out_buf.getvalue()
                b64 = base64.b64encode(out_bytes).decode("ascii")
                return f"data:{target_mime};base64,{b64}"
        except Exception as exc:
            logger.debug("PIL optimization failed, falling back to raw bytes: %s", exc)

    # Fallback: encode original bytes
    b64 = base64.b64encode(raw_bytes).decode("ascii")
    return f"data:{mime};base64,{b64}"


def _parse_flac_native(filepath: Path) -> Tuple[Optional[bytes], str, Dict[str, str]]:
    """
    Parse FLAC metadata blocks directly from binary header.
    Returns: (raw_image_bytes, mime, tags)
    """
    cover_bytes: Optional[bytes] = None
    cover_mime: str = ""
    is_front_cover: bool = False
    tags: Dict[str, str] = {}

    try:
        with open(filepath, "rb") as f:
            magic = f.read(4)
            if magic != b"fLaC":
                return None, "", tags

            while True:
                header = f.read(4)
                if len(header) < 4:
                    break

                is_last = bool(header[0] & 0x80)
                block_type = header[0] & 0x7F
                block_len = int.from_bytes(header[1:4], "big")

                if block_type == 4:  # VORBIS_COMMENT
                    comment_data = f.read(block_len)
                    tags.update(_parse_vorbis_comment_block(comment_data))

                elif block_type == 6:  # PICTURE
                    pic_data = f.read(block_len)
                    parsed = _parse_flac_picture_block(pic_data)
                    if parsed:
                        pic_type, mime, img_data = parsed
                        # Prefer Front Cover (type 3), else take the first picture found
                        if pic_type == 3 or not cover_bytes:
                            cover_bytes = img_data
                            cover_mime = mime
                            if pic_type == 3:
                                is_front_cover = True

                else:
                    # Skip other blocks (STREAMINFO, PADDING, SEEKTABLE, etc.)
                    f.seek(block_len, io.SEEK_CUR)

                if is_last:
                    break

    except Exception as exc:
        logger.debug("Native FLAC parser encountered an error: %s", exc)

    return cover_bytes, cover_mime, tags


def _parse_vorbis_comment_block(data: bytes) -> Dict[str, str]:
    """Parse Vorbis comment key-value pairs (little-endian lengths)."""
    tags: Dict[str, str] = {}
    if len(data) < 8:
        return tags

    try:
        vendor_len = struct.unpack("<I", data[0:4])[0]
        offset = 4 + vendor_len
        if offset + 4 > len(data):
            return tags

        num_comments = struct.unpack("<I", data[offset:offset + 4])[0]
        offset += 4

        for _ in range(num_comments):
            if offset + 4 > len(data):
                break
            c_len = struct.unpack("<I", data[offset:offset + 4])[0]
            offset += 4
            if offset + c_len > len(data):
                break
            comment_bytes = data[offset:offset + c_len]
            offset += c_len

            try:
                comment_str = comment_bytes.decode("utf-8", errors="replace")
                if "=" in comment_str:
                    k, v = comment_str.split("=", 1)
                    tags[k.strip().upper()] = v.strip()
            except Exception:
                continue
    except Exception as exc:
        logger.debug("Error parsing vorbis comment: %s", exc)

    return tags


def _parse_flac_picture_block(data: bytes) -> Optional[Tuple[int, str, bytes]]:
    """
    Parse a FLAC METADATA_BLOCK_PICTURE.
    Returns: (picture_type, mime_string, raw_image_bytes)
    """
    if len(data) < 32:
        return None

    try:
        pic_type, mime_len = struct.unpack(">II", data[0:8])
        offset = 8
        mime = data[offset:offset + mime_len].decode("latin1", errors="replace")
        offset += mime_len

        desc_len = struct.unpack(">I", data[offset:offset + 4])[0]
        offset += 4 + desc_len

        # width (4), height (4), depth (4), colors (4), data_len (4)
        if offset + 20 > len(data):
            return None

        _, _, _, _, data_len = struct.unpack(">IIIII", data[offset:offset + 20])
        offset += 20

        if offset + data_len > len(data):
            return None

        img_bytes = data[offset:offset + data_len]
        return pic_type, mime, img_bytes
    except Exception as exc:
        logger.debug("Error parsing FLAC picture block: %s", exc)
        return None


def _extract_ffmpeg_cover(filepath: Path) -> Optional[bytes]:
    """Fallback: extract attached picture using ffmpeg stdout pipe."""
    cmd = [
        "ffmpeg", "-v", "quiet",
        "-i", str(filepath),
        "-map", "0:v:0",
        "-c", "copy",
        "-f", "image2",
        "pipe:1",
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, timeout=15)
        if res.stdout and len(res.stdout) > 32:
            return res.stdout
    except Exception as exc:
        logger.debug("ffmpeg cover extraction failed: %s", exc)
    return None


def extract_cover_and_tags(
    filepath: Path | str,
    probe_dict: Optional[Dict[str, Any]] = None,
) -> Tuple[Optional[str], Dict[str, Optional[str]]]:
    """
    Extract album cover art (as data URL base64) and track tags (title, artist, album).

    Returns:
        (cover_art_base64, {"title": ..., "artist": ..., "album": ...})
    """
    p = Path(filepath)
    cover_raw_bytes: Optional[bytes] = None
    cover_mime: str = ""
    tags: Dict[str, str] = {}

    # 1. Native FLAC binary extraction (zero-subprocess, instantaneous)
    if p.suffix.lower() == ".flac" or p.name.lower().endswith(".flac"):
        cover_raw_bytes, cover_mime, tags = _parse_flac_native(p)

    # 2. If no cover found yet, try ffmpeg
    if not cover_raw_bytes:
        ffmpeg_bytes = _extract_ffmpeg_cover(p)
        if ffmpeg_bytes:
            cover_raw_bytes = ffmpeg_bytes
            cover_mime = _detect_mime_from_magic(ffmpeg_bytes)

    # 3. Fill in tags from probe_dict if missing
    if probe_dict:
        fmt_tags = probe_dict.get("format", {}).get("tags", {}) or {}
        for k, v in fmt_tags.items():
            upper_k = k.upper()
            if upper_k not in tags and v:
                tags[upper_k] = str(v)

    # Standardize tag keys
    title = tags.get("TITLE") or tags.get("TRACKTITLE") or tags.get("NAME")
    artist = tags.get("ARTIST") or tags.get("ALBUMARTIST") or tags.get("PERFORMER")
    album = tags.get("ALBUM")

    # 4. Convert cover image bytes to optimized Base64
    cover_art_b64: Optional[str] = None
    if cover_raw_bytes:
        cover_art_b64 = _optimize_and_encode_image(cover_raw_bytes, cover_mime)

    return cover_art_b64, {
        "title": title,
        "artist": artist,
        "album": album,
    }
