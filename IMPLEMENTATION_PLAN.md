# IMPLEMENTATION PLAN: TrueLossless Inspector (FLAC / Hi-Res / DSD Authenticity Analyzer)



## 1. Project Overview & Core Objective

Build a full-stack web application that analyzes lossless audio files (`.flac`, `.wav`, `.alac`, `.ape`, `.wv`) and DSD files (`.dsf`, `.dff`) to determine whether they are **Authentic Lossless (CD Rip / Studio Master)** or **Fake / Upscaled (Transcoded from lossy MP3/AAC/Opus, bit-padded from 16-bit to 24-bit, or spoofed with high-frequency white noise)**.



### Critical Engineering Constraints for the AI Agent

1. **Never normalize PCM to float before Bit-Depth Analysis:** You MUST inspect raw integer PCM samples (`int32`) first to detect least-significant-bit (LSB) zero-padding.

2. **Memory-Safe Processing:** Audio files can exceed 150 MB (especially 24-bit/192kHz FLAC or DSD64/DSD128). Do NOT load entire multi-minute uncompressed DSD/Hi-Res streams into RAM at once for STFT. Use segmented window sampling (top 20% highest RMS energy frames).

3. **Probabilistic Verdict & Acoustic Edge Cases:** Output both a deterministic technical readout and a weighted **Authenticity Score (0–100)** with confidence levels, accounting for vintage masters or solo acoustic tracks that naturally lack energy above 16 kHz.



---



## 2. Tech Stack & System Requirements



### Backend (Python 3.11+)

- **Framework:** `FastAPI` + `uvicorn` + `python-multipart`

- **Audio & DSP Engine:** `numpy`, `scipy` (`scipy.signal.stft`, `scipy.signal.savgol_filter`, `scipy.stats.pearsonr`), `soundfile` (libsndfile wrapper)

- **Visualization:** `matplotlib` (headless `Agg` backend for rendering high-contrast annotated spectrogram PNGs)

- **System Dependency:** `ffmpeg` and `ffprobe` (must be invoked via `subprocess` for container metadata extraction and DSD `.dsf`/`.dff` to PCM conversion)



### Frontend

- **Stack:** React (Vite + TypeScript) + TailwindCSS + Lucide Icons (or single-command static mount served by FastAPI if requested)

- **Features:** Drag-and-drop audio uploader, real-time analysis progress, Verdict Badge (`AUTHENTIC`, `SUSPICIOUS`, `FAKE / TRANSCODED`, `FAKE BIT-DEPTH`), 4-Pillar Diagnostic Cards, Interactive Frequency Roll-off Curve, and Annotated Spectrogram Viewer.



---



## 3. Directory Structure



```text

truelossless-inspector/

├── backend/

│   ├── main.py                  # FastAPI app, CORS, upload routes, cleanup middleware

│   ├── config.py                # Constants, frequency thresholds, scoring weights

│   ├── schemas.py               # Pydantic response models

│   ├── core/

│   │   ├── ingestion.py         # ffprobe metadata + memory-safe int32/float32 PCM loader

│   │   ├── bit_depth.py         # Pillar 1: Bitwise LSB padding & wasted bits analyzer

│   │   ├── spectral_cutoff.py   # Pillar 2: High-RMS frame selection & STFT roll-off detector

│   │   ├── anti_spoof.py        # Pillar 3: Spectral holes (12-16kHz) & fake noise correlation

│   │   ├── ultrasonic.py        # Pillar 4: Hi-Res (>48kHz) & DSD ultrasonic transient checker

│   │   ├── spectrogram.py       # Headless Matplotlib spectrogram renderer with cutoff annotations

│   │   └── scorer.py            # Heuristic decision tree & Authenticity Score (0-100)

│   └── tests/

│       ├── generate_fixtures.py # Script to synthesize True vs. Fake FLAC test files

│       └── test_pipeline.py     # Pytest suite verifying all 4 DSP pillars

├── frontend/

│   ├── src/

│   │   ├── components/

│   │   │   ├── UploadZone.tsx

│   │   │   ├── VerdictBanner.tsx

│   │   │   ├── MetricsGrid.tsx

│   │   │   ├── RolloffChart.tsx

│   │   │   └── SpectrogramModal.tsx

│   │   ├── App.tsx

│   │   └── api.ts

└── requirements.txt

```



---



## 4. Detailed DSP Pipeline & Mathematical Specifications



### Module 0: Audio Ingestion & Smart Sampling (`core/ingestion.py`)

1. **Metadata Extraction:** Run `ffprobe -v quiet -print_format json -show_format -show_streams <filepath>` to extract:

   - `codec_name`, `sample_rate` ($f_s$), `bits_per_raw_sample` (or `bits_per_sample`), `duration`, `bit_rate`.

2. **DSD Handling (`.dsf`, `.dff`):**

   - Flag `is_dsd = True`.

   - Convert a maximum 60-second slice from the middle of the track to 24-bit / 88.2 kHz PCM via `ffmpeg` pipe (`-f s32le -acodec pcm_s32le -ar 88200`) for spectral and ultrasonic inspection.

3. **Standard PCM/FLAC/WAV Handling:**

   - Read raw integer samples using `soundfile.read(filepath, dtype='int32', always_2d=True)` in chunks of 10 seconds (up to 60 seconds total taken from 20%, 50%, and 80% positions of the track if duration > 90s).

   - Keep a copy of raw `int32` samples for **Module 1**, then normalize to `float32` in range `[-1.0, 1.0]` by dividing by $2^{31}$ for **Modules 2, 3, and 4**.

   - Merge stereo channels to mono (`np.mean(samples, axis=1)`) ONLY after checking whether left/right channels have identical high-frequency noise (a common sign of fake stereo dither).



---



### Module 1: True Bit-Depth & Wasted Bits Analyzer (`core/bit_depth.py`)

**Objective:** Detect files declared as 24-bit that actually contain 16-bit audio padded with trailing zeros (`00000000`), or software gain-scaled 16-bit files.



1. Note that `soundfile` left-shifts 16-bit and 24-bit integer data into a 32-bit signed integer (`int32`):

   - True 16-bit occupies bits `[16..31]`; bits `[0..15]` are always `0`.

   - True 24-bit occupies bits `[8..31]`; bits `[0..7]` are always `0`.

2. **Algorithm:**

   - Compute bitwise OR across all non-zero raw `int32` samples:

     `combined_bits = np.bitwise_or.reduce(np.abs(raw_int32_samples))`

   - Count trailing zero bits ($Z_{trail}$) of `combined_bits` from LSB (bit 0) upward.

   - Calculate **Effective Bit Depth**:

     $$\text{Effective Bit Depth} = 32 - Z_{trail}$$

   - **Per-Frame LSB Entropy Check (Anti-Gain-Scaling Check):** Even if a 16-bit file had its volume changed by `0.1 dB` in 24-bit space (activating the lower 8 bits mathematically), check the histogram distribution of `samples & 0xFF00` (bits 8–15). If fewer than 16 distinct values appear in the bottom 8 bits across 1,000,000 samples, flag as `SUSPICIOUS_BIT_SCALING`.

3. **Output Metrics:** `declared_bit_depth`, `effective_bit_depth`, `wasted_bits`, `is_bit_padded` (boolean).



---



### Module 2: High-RMS Frame Selection & STFT Cutoff Detector (`core/spectral_cutoff.py`)

**Objective:** Accurately detect brickwall low-pass filter cutoffs caused by MP3, AAC, Opus, or Vorbis encoders without being fooled by quiet intro/outro sections.



1. **High-Energy Frame Filtering:**

   - Slice the `float32` signal into non-overlapping 1-second frames.

   - Compute Root Mean Square (RMS) energy for each frame: $E_{rms} = \sqrt{\frac{1}{N}\sum x[n]^2}$.

   - Select the **top 20% highest RMS frames** (minimum 5 frames). Concatenate or process only these active frames.

2. **STFT Calculation:**

   - Choose `nperseg` dynamically so frequency bin resolution $\Delta f \approx 10\text{ Hz}$:

     - For $f_s \le 48000$: `nperseg = 4096`, `noverlap = 2048`, `window = 'hann'`.

     - For $f_s > 48000$: `nperseg = 8192`, `noverlap = 4096`, `window = 'hann'`.

   - Compute magnitude matrix $\vert{}Z(f, t)\vert{}$ and convert to decibels relative to full scale (dBFS):

     $$S_{\text{dB}}(f, t) = 20 \cdot \log_{10}(\max(\vert{}Z(f, t)\vert{}, 10^{-7}))$$

3. **95th Percentile Spectral Profile & Gradient Search:**

   - For each frequency bin $f_i$, compute the **95th percentile energy** across the selected loud time frames: $P_{95}(f_i)$. (Using the 95th percentile instead of the mean captures transient peaks like hi-hats and cymbals that reach 22 kHz).

   - Smooth $P_{95}(f)$ using `savgol_filter(P_95, window_length=21, polyorder=3)`.

   - Search from $21.5\text{ kHz}$ downward to $11.0\text{ kHz}$ using a sliding window of width $\Delta W = 500\text{ Hz}$:

     - Calculate energy drop: $\Delta \text{dB}(f) = P_{95}(f - \Delta W) - P_{95}(f + \Delta W)$.

     - Calculate the mean noise floor above $f + \Delta W$ up to Nyquist ($f_N = f_s / 2$).

     - A **Brickwall Cutoff ($f_c$)** is detected at frequency $f$ if:

       1. $\Delta \text{dB}(f) \ge 28\text{ dB}$ within $500\text{ Hz}$ (slope steeper than $-56\text{ dB/kHz}$), AND

       2. The average energy above $f + 500\text{ Hz}$ remains within $6\text{ dB}$ of the digital noise floor (below $-95\text{ dBFS}$).

4. **Encoder Fingerprint Mapping:**

   - $f_c \in [15.5, 16.5]\text{ kHz}$: Likely MP3 128 kbps / Standard YouTube AAC / Old Vorbis.

   - $f_c \in [17.5, 19.3]\text{ kHz}$: Likely MP3 192–256 kbps / AAC 192 kbps.

   - $f_c \in [19.8, 20.6]\text{ kHz}$: Likely MP3 320 kbps (LAME low-pass filter default at $20.5\text{ kHz}$) or Opus 160+ kbps.

   - $f_c \ge 21.8\text{ kHz}$ (when $f_s = 44.1\text{ kHz}$): Full Redbook CD bandwidth.



---



### Module 3: Anti-Spoofing Detector — Spectral Holes & Fake White Noise (`core/anti_spoof.py`)

**Objective:** Catch scammers who take a 128/320 kbps MP3 and inject synthetic white noise / dither above 16 kHz to fool visual spectrogram inspection.



1. **Test A: Mid-High Spectral Sparsity ("MP3 Spectral Holes" in 12 kHz – 16 kHz):**

   - Lossy MDCT codecs aggressively quantize masked frequency bins to zero in the $12\text{ kHz} - 16\text{ kHz}$ band, creating dark "swiss-cheese" holes even in loud passages.

   - In the STFT matrix $S_{\text{dB}}(f, t)$ of the top 20% loudest frames, isolate frequency bins between $12\text{ kHz}$ and $15.8\text{ kHz}$.

   - Compute the median energy $M_{12-16}$ of this sub-band.

   - Calculate **Sparsity Ratio ($R_{\text{hole}}$)**: fraction of time-frequency bins in $12-15.8\text{ kHz}$ where energy drops more than $35\text{ dB}$ below $M_{12-16}$.

   - If $R_{\text{hole}} > 0.38$, flag `SPECTRAL_HOLES_DETECTED = True`.



2. **Test B: High-Frequency Temporal Envelope Correlation (Anti-Noise-Padding):**

   - In genuine recordings, high-frequency energy ($16.5\text{ kHz} - 21.5\text{ kHz}$) is produced by acoustic transients (cymbals, snares, sibilance) that co-occur in time with upper-mid transients ($3\text{ kHz} - 8\text{ kHz}$).

   - Extract the time-series mean energy envelope $E_{\text{mid}}(t)$ for $[3\text{ kHz}, 8\text{ kHz}]$ and $E_{\text{high}}(t)$ for $[16.5\text{ kHz}, 21.5\text{ kHz}]$ across all frames.

   - Compute Pearson correlation coefficient $r = \text{pearsonr}(E_{\text{mid}}(t), E_{\text{high}}(t))$ and temporal standard deviation $\sigma_{\text{high}} = \text{std}(E_{\text{high}}(t))$.

   - **Spoof Detection Rule:** If energy exists above $16.5\text{ kHz}$ ($> -90\text{ dBFS}$), BUT:

     - $r < 0.12$ (high frequencies do not move with the music) AND

     - $\sigma_{\text{high}} < 2.5\text{ dB}$ (stationary flat noise floor),

     then flag `FAKE_NOISE_INJECTION = True`.



---



### Module 4: Hi-Res & DSD Ultrasonic Analyzer (`core/ultrasonic.py`)

**Objective:** Validate files with $f_s \ge 88.2\text{ kHz}$ or DSD files.



1. **Upsampled CD Check:**

   - Inspect energy drop across the $22.05\text{ kHz}$ (for $88.2/176.4\text{ kHz}$) or $24.0\text{ kHz}$ (for $96/192\text{ kHz}$) boundary.

   - If a brickwall drop $\ge 30\text{ dB}$ occurs right at $22.05\text{ kHz}$ or $24.0\text{ kHz}$, flag `FAKE_HIRES_UPSAMPLED = True` (44.1/48 kHz master upsampled to Hi-Res container).

2. **DSD / Ultrasonic Noise vs. Musical Signal ($23\text{ kHz} - 40\text{ kHz}$):**

   - DSD64 naturally exhibits a rising ultrasonic quantization noise floor above $24\text{ kHz}$ due to 1-bit Sigma-Delta modulation.

   - Compute Pearson correlation $r_{\text{ultra}}$ between the audible transient envelope $[4\text{ kHz}, 12\text{ kHz}]$ and the ultrasonic band $[23\text{ kHz}, 36\text{ kHz}]$.

   - If the file is transcoded from a $44.1\text{ kHz}$ source or MP3 into DSD, the ultrasonic band will contain *only* uncorrelated Sigma-Delta noise ($r_{\text{ultra}} < 0.08$) with a visible notch/shelf at $20\text{ kHz}$ or $22.05\text{ kHz}$.



---



## 5. Scoring Matrix & Verdict Engine (`core/scorer.py`)



Start with `base_score = 100` and apply deterministic deductions:



| Condition Detected | Score Deduction | Flag / Verdict Impact |

| :--- | :--- | :--- |

| Brickwall cutoff $f_c \le 16.8\text{ kHz}$ | `-75` | `FAKE_UPSCALED` (Likely MP3 128k / YouTube rip) |

| Brickwall cutoff $16.8\text{ kHz} < f_c \le 19.5\text{ kHz}$ | `-65` | `FAKE_UPSCALED` (Likely MP3 192-256k / AAC) |

| Brickwall cutoff $19.5\text{ kHz} < f_c \le 20.7\text{ kHz}$ | `-50` | `SUSPICIOUS_TRANSCODE` (Likely MP3 320k / Opus) |

| `FAKE_NOISE_INJECTION == True` | `-80` | `FAKE_SPOOFED` (Lossy file with synthetic noise) |

| `SPECTRAL_HOLES_DETECTED == True` ($R_{\text{hole}} > 0.38$) | `-35` | Confirms lossy MDCT compression history |

| `is_bit_padded == True` (e.g., 24-bit container with 16-bit LSBs) | `-30` | `FAKE_BIT_DEPTH` (Bloated container) |

| `FAKE_HIRES_UPSAMPLED == True` (Cutoff at 22.05/24 kHz in 96k+ file) | `-40` | `UPSAMPLED_HIRES` (Standard Redbook audio in Hi-Res wrapper) |

| Gradual roll-off below 18 kHz WITHOUT brickwall slope ($> -20\text{ dB/kHz}$) and $R_{\text{hole}} < 0.15$ | `-10` | `AUTHENTIC_WITH_NOTE` (Natural acoustic roll-off / vintage master) |



**Final Classification:**

- `85 – 100`: **Authentic Lossless** (Green)

- `55 – 84`: **Suspicious / Upsampled Container** (Amber)

- `0 – 54`: **Fake Lossless / Transcoded from Lossy** (Red)



---



## 6. REST API Contract (`POST /api/analyze`)



Return the following JSON schema:



```json

{

  "filename": "track01.flac",

  "verdict": {

    "score": 25,

    "status": "FAKE_UPSCALED",

    "label": "Fake Lossless (Transcoded from MP3 ~320kbps)",

    "confidence": "HIGH",

    "summary": "Detected a sharp brickwall frequency cutoff at 20.45 kHz (-68 dB/kHz slope) and MDCT quantization holes in the 12-16 kHz band."

  },

  "metadata": {

    "codec": "FLAC",

    "sample_rate_hz": 44100,

    "channels": 2,

    "duration_sec": 214.5,

    "bitrate_kbps": 945

  },

  "pillars": {

    "bit_depth": {

      "declared": 24,

      "effective": 16,

      "wasted_bits": 8,

      "is_padded": true,

      "detail": "Bottom 8 LSBs are permanently zero. File is 16-bit padded to 24-bit."

    },

    "spectral_cutoff": {

      "nyquist_hz": 22050,

      "detected_cutoff_hz": 20450,

      "rolloff_slope_db_per_khz": -68.4,

      "is_brickwall": true,

      "suspected_source_encoder": "MP3 320 kbps (LAME)"

    },

    "anti_spoof": {

      "spectral_holes_ratio": 0.44,

      "holes_detected": true,

      "hf_envelope_correlation": 0.41,

      "fake_noise_injected": false

    },

    "ultrasonic": {

      "applicable": false,

      "has_true_ultrasonic_transients": null

    }

  },

  "visuals": {

    "rolloff_curve": {

      "frequencies_khz": [0.5, 1.0, 2.0, "... up to Nyquist"],

      "energy_dbfs": [-14.2, -16.8, -21.0, "..."]

    },

    "spectrogram_base64": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUg..."

  }

}

```



---



## 7. Step-by-Step Execution Plan for the AI Agent



Execute this build in **4 strict sequential phases**. Do not skip Phase 2 testing.



### Phase 1: Project Setup & Core Ingestion

1. Initialize `backend/` virtual environment and install `fastapi`, `uvicorn`, `python-multipart`, `numpy`, `scipy`, `soundfile`, `matplotlib`, `pytest`, `httpx`.

2. Implement `core/ingestion.py` with `ffprobe` metadata parsing and segmented `int32` + `float32` loading.



### Phase 2: Implement the 4 DSP Pillars & Automated Verification (CRITICAL)

1. Implement `bit_depth.py`, `spectral_cutoff.py`, `anti_spoof.py`, `ultrasonic.py`, and `scorer.py`.

2. Create `backend/tests/generate_fixtures.py` using `numpy` and `scipy.signal` (plus `ffmpeg` CLI) to programmatically synthesize 4 short (8-second) `.flac` test fixtures containing broadband musical transients (bursts of pink noise + harmonic chirps):

   - `true_24bit.flac`: Genuine full-spectrum 24-bit / 44.1 kHz signal reaching 22.05 kHz.

   - `padded_24bit.flac`: 16-bit signal bit-shifted into a 24-bit FLAC container.

   - `fake_mp3_128.flac`: Signal encoded to 128 kbps MP3 via `ffmpeg`, then decoded back into `.flac`.

   - `spoofed_noise.flac`: The 128 kbps MP3 transcode mixed with low-level stationary high-passed white noise (`>16 kHz`) at `-75 dBFS`.

3. Run `pytest backend/tests/test_pipeline.py` and verify that:

   - `true_24bit.flac` scores $\ge 90$ (`AUTHENTIC_LOSSLESS`).

   - `padded_24bit.flac` triggers `is_padded == True` and `effective == 16`.

   - `fake_mp3_128.flac` detects $f_c \approx 16.0\text{ kHz}$ and scores $< 40$.

   - `spoofed_noise.flac` triggers `fake_noise_injected == True` via low temporal correlation.



### Phase 3: Spectrogram Renderer & FastAPI Endpoint

1. Implement `core/spectrogram.py`:

   - Render a $1200 \times 500$ px dark-mode spectrogram (`magma` or `inferno` colormap, `-120 dBFS` to `0 dBFS`).

   - Draw a horizontal cyan dashed line at `detected_cutoff_hz` with a text badge (e.g., `"Detected Cutoff: 16.0 kHz"`).

   - Return as a Base64-encoded PNG string and clean up temporary uploaded files in a `finally` block.

2. Expose `POST /api/analyze` and `GET /api/health` in `main.py`.



### Phase 4: Frontend Dashboard UI

1. Build a dark-themed audiophile dashboard (inspired by Spek + FiiO/foobar2000 dark aesthetics):

   - **Drag & Drop Upload Card** supporting `.flac`, `.wav`, `.dsf`, `.dff`.

   - **Verdict Header** showing the 0–100 circular gauge, status badge, and human-readable diagnostic summary.

   - **4 Diagnostic Pillar Cards** displaying Bit-Depth integrity (with visual 24-bit slot bar showing active vs. dead bits), Cutoff Frequency, Anti-Spoofing Correlation, and Hi-Res Ultrasonic status.

   - **Dual Visual Panel:** Interactive 95th-percentile Spectral Roll-off line chart (`Recharts` or `Chart.js`) stacked above the high-resolution annotated Spectrogram image with zoom/fullscreen toggle.
