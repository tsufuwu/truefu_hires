# TrueLossless Inspector 🎵🔍

> **FLAC / Hi-Res / DSD Authenticity Analyzer**
> A full-stack audiophile web application and DSP engine to detect fake lossless audio (lossy transcodes, bit-padding, and synthetic high-frequency noise injection).

---

## 🚀 Key Features & The 4 DSP Pillars

1. **Pillar 1: True Bit-Depth & Wasted Bits Analyzer (`core/bit_depth.py`)**
   - Inspects raw integer `int32` PCM samples (preventing float-normalization false negatives).
   - Bitwise analysis computes effective bit depth ($32 - Z_{\text{trail}}$) to catch 16-bit audio padded with zero bytes into a 24-bit container.
   - Per-frame LSB entropy analysis catches artificial gain-scaling tampering.

2. **Pillar 2: High-RMS Frame Selection & Spectral Cutoff Detector (`core/spectral_cutoff.py`)**
   - Selects top 20% highest RMS energy frames to prevent quiet sections from skewing frequency analysis.
   - High-resolution STFT + 95th-percentile spectral profiling with Savitzky-Golay filtering.
   - Detects brickwall steep low-pass filter drops ($\ge 28\text{ dB}$ within $500\text{ Hz}$, slope steeper than $-56\text{ dB/kHz}$) and maps encoder signatures:
     - $14.0 - 16.8\text{ kHz}$: MP3 ~128 kbps / YouTube AAC / Vorbis
     - $16.8 - 19.5\text{ kHz}$: MP3 ~192–256 kbps / AAC
     - $19.5 - 20.7\text{ kHz}$: MP3 ~320 kbps (LAME) / Opus
     - $> 20.7\text{ kHz}$: Genuine Redbook CD audio / Studio Master

3. **Pillar 3: Anti-Spoofing & Fake Noise Detector (`core/anti_spoof.py`)**
   - **Mid-High Spectral Sparsity (12–15.8 kHz):** Uncovers MDCT quantization "swiss-cheese" holes characteristic of lossy codecs.
   - **Temporal Envelope Correlation:** Computes Pearson correlation $r$ between upper-mid transients ($3-8\text{ kHz}$) and ultrasonic/HF ($16.5-21.5\text{ kHz}$). Catches synthetic white noise or dither injected to deceive spectrograms ($r < 0.12$ and stationary variance).

4. **Pillar 4: Hi-Res & DSD Ultrasonic Analyzer (`core/ultrasonic.py`)**
   - **Upsampled CD Check:** Brickwall drops at $22.05\text{ kHz}$ or $24.0\text{ kHz}$ in $\ge 88.2\text{ kHz}$ containers.
   - **DSD Transcode Inspection:** Distinguishes genuine musical ultrasonic harmonics from pure Sigma-Delta quantization noise.

---

## 🛠️ Tech Stack

- **Backend:** FastAPI, Uvicorn, SciPy, NumPy, SoundFile, Matplotlib (headless `Agg`), Pydantic
- **Frontend:** React 19, TypeScript, Vite, Chart.js, Lucide Icons, Glassmorphic Audiophile Dark Theme
- **Testing:** Pytest, FastApi TestClient, automated synthetic audio fixture generator (`generate_test_audio.py`)

---

## 🏃 Quick Start

### 1. Run the Backend & Frontend (Single-Command Mode)
The FastAPI server serves both the REST API and the pre-built React frontend:

```bash
# Activate virtual environment
backend\.venv\Scripts\activate

# Start server
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```
Open your browser at **`http://localhost:8000`**.

### 2. Run Frontend Development Server (Optional)
If developing the React UI with hot module replacement:

```bash
cd frontend
npm run dev
```

### 3. Run Automated DSP & API Tests
Run all 22 tests verifying all 4 DSP pillars and API endpoints against synthetic fixtures:

```bash
backend\.venv\Scripts\pytest -v backend/tests
```

---

## 📊 Verification Test Matrix

| Fixture File | Type | Expected Result | Pytest Status |
| :--- | :--- | :--- | :--- |
| `true_24bit.flac` | Genuine 24-bit/44.1kHz | Score $\ge 90$, Status `AUTHENTIC_LOSSLESS` | ✅ PASSED |
| `padded_24bit.flac` | 16-bit padded to 24-bit | `is_padded == True`, effective $\le 17$, score $\le 70$ | ✅ PASSED |
| `fake_mp3_128.flac` | Transcoded from 128k MP3 | Brickwall $f_c \approx 16\text{–}17\text{ kHz}$, score $< 40$, status `FAKE` | ✅ PASSED |
| `spoofed_noise.flac` | 128k MP3 + noise floor | Brickwall/holes detected, score $< 55$ | ✅ PASSED |
| REST API Endpoints | `/api/health`, `/api/analyze`, static mount | HTTP 200, schema validated | ✅ PASSED |

---

## 💖 Donate / Ủng Hộ

Nếu Truefu Hires hữu ích với bạn, bạn có thể ủng hộ tác giả phát triển dự án tại:
👉 [https://tsufu.gitbook.io/donate](https://tsufu.gitbook.io/donate)

