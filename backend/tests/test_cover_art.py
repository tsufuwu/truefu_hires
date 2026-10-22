from __future__ import annotations

import struct
import sys
import tempfile
from pathlib import Path

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))
sys.path.insert(0, str(backend_dir.parent))

from core.cover_art import extract_cover_and_tags


def test_native_flac_cover_and_tags_extraction():
    # Build a minimal valid FLAC container with STREAMINFO, VORBIS_COMMENT and PICTURE blocks
    sample_flac = bytearray(b"fLaC")

    # Block 0: STREAMINFO (mandatory 34 bytes), not last (0x00)
    streaminfo = b"\x00" * 34
    sample_flac.extend(bytes([0x00]))  # block_type 0, not last
    sample_flac.extend(struct.pack(">I", len(streaminfo))[1:])  # 3 bytes length
    sample_flac.extend(streaminfo)

    # Block 4: VORBIS_COMMENT, not last (0x04)
    vendor = b"TrueLossless Test"
    comments = [b"TITLE=Test Track", b"ARTIST=Test Artist", b"ALBUM=Lossless Album"]
    vc_data = bytearray(struct.pack("<I", len(vendor)) + vendor)
    vc_data.extend(struct.pack("<I", len(comments)))
    for c in comments:
        vc_data.extend(struct.pack("<I", len(c)) + c)

    sample_flac.extend(bytes([0x04]))
    sample_flac.extend(struct.pack(">I", len(vc_data))[1:])
    sample_flac.extend(vc_data)

    # Block 6: PICTURE, last block (0x80 | 0x06 = 0x86)
    mime = b"image/jpeg"
    desc = b"Cover Front"
    # Minimal JPEG SOI + APP0 marker + EOI
    jpeg_data = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xff\xdb\x00C\x00\xff\xd9"
    pic_data = (
        struct.pack(">II", 3, len(mime))
        + mime
        + struct.pack(">I", len(desc))
        + desc
        + struct.pack(">IIIII", 100, 100, 24, 0, len(jpeg_data))
        + jpeg_data
    )

    sample_flac.extend(bytes([0x86]))  # block_type 6, is_last=True
    sample_flac.extend(struct.pack(">I", len(pic_data))[1:])
    sample_flac.extend(pic_data)

    with tempfile.NamedTemporaryFile(suffix=".flac", delete=False) as tmp:
        tmp.write(sample_flac)
        tmp_path = Path(tmp.name)

    try:
        cover_b64, tags = extract_cover_and_tags(tmp_path)
        assert cover_b64 is not None
        assert cover_b64.startswith("data:image/")
        assert tags["title"] == "Test Track"
        assert tags["artist"] == "Test Artist"
        assert tags["album"] == "Lossless Album"
    finally:
        if tmp_path.exists():
            tmp_path.unlink()
