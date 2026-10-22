"""
tests/test_api.py — Pytest suite for FastAPI REST endpoints (/api/health and /api/analyze).
"""
from __future__ import annotations

import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

# Allow imports from backend/ and root
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))
sys.path.insert(0, str(backend_dir.parent))

try:
    from backend.main import app
except ModuleNotFoundError:
    from main import app

client = TestClient(app)
FIXTURE_DIR = Path(__file__).parent / "fixtures"


def test_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "Truefu" in data["service"]


def test_root_serves_frontend():
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")


def test_analyze_unsupported_format():
    response = client.post(
        "/api/analyze",
        files={"file": ("test.mp3", b"fake mp3 content", "audio/mpeg")},
    )
    assert response.status_code == 415
    assert "Unsupported file type" in response.json()["detail"]


def test_analyze_true_24bit_api():
    path = FIXTURE_DIR / "true_24bit.flac"
    if not path.exists():
        pytest.skip(f"Fixture not found: {path}")

    with open(path, "rb") as f:
        response = client.post(
            "/api/analyze",
            files={"file": ("true_24bit.flac", f, "audio/flac")},
        )

    assert response.status_code == 200
    data = response.json()

    assert data["filename"] == "true_24bit.flac"
    assert data["verdict"]["score"] >= 90
    assert data["verdict"]["status"] == "AUTHENTIC_LOSSLESS"
    assert data["pillars"]["bit_depth"]["effective"] >= 20
    assert not data["pillars"]["bit_depth"]["is_padded"]
    assert data["visuals"]["spectrogram_base64"] is not None
    assert len(data["visuals"]["rolloff_curve"]["frequencies_khz"]) > 0


def test_analyze_padded_24bit_api():
    path = FIXTURE_DIR / "padded_24bit.flac"
    if not path.exists():
        pytest.skip(f"Fixture not found: {path}")

    with open(path, "rb") as f:
        response = client.post(
            "/api/analyze",
            files={"file": ("padded_24bit.flac", f, "audio/flac")},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["pillars"]["bit_depth"]["is_padded"] is True
    assert data["pillars"]["bit_depth"]["effective"] <= 17
    assert data["verdict"]["score"] <= 70


def test_analyze_fake_mp3_api():
    path = FIXTURE_DIR / "fake_mp3_128.flac"
    if not path.exists():
        pytest.skip(f"Fixture not found: {path}")

    with open(path, "rb") as f:
        response = client.post(
            "/api/analyze",
            files={"file": ("fake_mp3_128.flac", f, "audio/flac")},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["pillars"]["spectral_cutoff"]["is_brickwall"] is True
    assert data["verdict"]["score"] < 40
    assert "FAKE" in data["verdict"]["status"] or "SUSPICIOUS" in data["verdict"]["status"]
    assert data["pillars"]["spectral_cutoff"]["suspected_source_encoder"] is not None


def test_analyze_spoofed_noise_api():
    path = FIXTURE_DIR / "spoofed_noise.flac"
    if not path.exists():
        pytest.skip(f"Fixture not found: {path}")

    with open(path, "rb") as f:
        response = client.post(
            "/api/analyze",
            files={"file": ("spoofed_noise.flac", f, "audio/flac")},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["verdict"]["score"] < 55


def test_list_samples_api():
    response = client.get("/api/samples")
    assert response.status_code == 200
    samples = response.json()
    assert len(samples) == 4
    ids = [s["id"] for s in samples]
    assert "authentic-24bit" in ids
    assert "fake-mp3" in ids


def test_analyze_sample_endpoint():
    response = client.post("/api/analyze-sample/authentic-24bit")
    assert response.status_code == 200
    data = response.json()
    assert data["verdict"]["score"] >= 90
    assert data["verdict"]["status"] == "AUTHENTIC_LOSSLESS"

    # Test invalid sample
    bad_resp = client.post("/api/analyze-sample/non-existent-sample")
    assert bad_resp.status_code == 404


def test_analyze_studio_filter_api(tmp_path):
    import io
    import numpy as np
    import soundfile as sf
    from scipy import signal
    from tests.generate_fixtures import make_broadband_signal

    sr = 44_100
    sig = make_broadband_signal(sr, sr * 8)
    sos = signal.butter(12, 21850, "low", fs=sr, output="sos")
    filtered = signal.sosfilt(sos, sig)
    stereo = np.column_stack([filtered, filtered * 0.98])

    buf = io.BytesIO()
    sf.write(buf, stereo, sr, format="FLAC", subtype="PCM_16")
    buf.seek(0)

    response = client.post(
        "/api/analyze",
        files={"file": ("studio_master_16bit.flac", buf, "audio/flac")},
    )

    assert response.status_code == 200
    data = response.json()
    cutoff_data = data["pillars"]["spectral_cutoff"]
    assert cutoff_data["is_studio_filter"] is True
    assert cutoff_data["is_brickwall"] is False
    assert 21_500.0 <= cutoff_data["detected_cutoff_hz"] <= 22_050.0
    assert "Studio Anti-Aliasing Filter" in cutoff_data["suspected_source_encoder"]


