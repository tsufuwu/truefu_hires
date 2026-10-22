import io
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf
from PIL import Image

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))
sys.path.insert(0, str(backend_dir.parent))

from core.cover_art import extract_cover_and_tags


def test_real_ffmpeg_flac_embedded_cover_and_tags():
    sr = 44100
    t = np.linspace(0, 1, sr, endpoint=False)
    audio = np.sin(2 * np.pi * 440 * t).astype(np.float32)
    stereo = np.column_stack([audio, audio])

    with tempfile.NamedTemporaryFile(suffix=".flac", delete=False) as f_audio:
        audio_path = f_audio.name
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f_img:
        img_path = f_img.name
    with tempfile.NamedTemporaryFile(suffix=".flac", delete=False) as f_out:
        out_path = f_out.name

    try:
        sf.write(audio_path, stereo, sr, format="FLAC", subtype="PCM_16")

        img = Image.new("RGB", (120, 120), color=(34, 211, 238))
        img.save(img_path, format="JPEG")

        cmd = [
            "ffmpeg", "-y",
            "-i", audio_path,
            "-i", img_path,
            "-map", "0:a",
            "-map", "1:v",
            "-c:a", "copy",
            "-c:v", "copy",
            "-metadata", "title=Test Flac Song",
            "-metadata", "artist=Inspector Band",
            "-metadata", "album=Album Test",
            "-disposition:v", "attached_pic",
            out_path,
        ]
        res = subprocess.run(cmd, capture_output=True)
        assert res.returncode == 0, res.stderr.decode("utf-8", errors="replace")

        cover_b64, tags = extract_cover_and_tags(out_path)
        assert cover_b64 is not None
        assert cover_b64.startswith("data:image/")
        assert tags["title"] == "Test Flac Song"
        assert tags["artist"] == "Inspector Band"
        assert tags["album"] == "Album Test"
    finally:
        for p in [audio_path, img_path, out_path]:
            if os.path.exists(p):
                os.unlink(p)
