"""
config.py — Central constants, frequency thresholds, and scoring weights
for the TrueLossless Inspector DSP pipeline.
"""

# ── Temporary upload directory (relative to backend/) ──────────────────────
UPLOAD_DIR = "uploads"
MAX_UPLOAD_MB = 512

# ── Audio ingestion ─────────────────────────────────────────────────────────
SUPPORTED_EXTENSIONS = {".flac", ".wav", ".alac", ".ape", ".wv", ".dsf", ".dff"}
DSD_EXTENSIONS = {".dsf", ".dff"}

# Maximum seconds of audio to analyse per pillar
MAX_ANALYSIS_SECONDS = 60

# Number of 10-s chunks to sample from long tracks (at 20 %, 50 %, 80 % positions)
SAMPLE_POSITIONS = [0.20, 0.50, 0.80]
CHUNK_DURATION_SEC = 10

# DSD-to-PCM conversion: target 24-bit / 88.2 kHz
DSD_PCM_SAMPLE_RATE = 88200
DSD_SLICE_SECONDS = 60          # seconds taken from the middle of the track

# ── Bit-depth analysis ──────────────────────────────────────────────────────
# Number of samples to inspect for per-frame LSB entropy check
LSB_ENTROPY_SAMPLE_LIMIT = 1_000_000
# Minimum distinct values in bottom-byte histogram to be considered real 24-bit
MIN_DISTINCT_BOTTOM_BYTE_VALUES = 16

# ── STFT parameters ─────────────────────────────────────────────────────────
STFT_NPERSEG_LOW  = 4096    # for sample_rate ≤ 48 000 Hz
STFT_NPERSEG_HIGH = 8192    # for sample_rate > 48 000 Hz
STFT_NOVERLAP_LOW  = 2048
STFT_NOVERLAP_HIGH = 4096

# Percentile used for spectral profile:
# 80th percentile is robust against percussive transient splatter (clicks/hi-hats)
# that artificially elevate the 95th percentile in lossy stopbands.
SPECTRAL_PERCENTILE = 80

# Savitzky-Golay smoother parameters
SAVGOL_WINDOW = 21
SAVGOL_POLY   = 3

# ── Cutoff detection ─────────────────────────────────────────────────────────
CUTOFF_SEARCH_LOW_HZ   = 11_000.0   # lower bound of brickwall search
CUTOFF_SEARCH_HIGH_HZ  = 22_050.0   # upper bound allows inspecting full Nyquist band
CUTOFF_WINDOW_HZ       = 500.0      # sliding window half-width

# Studio Anti-Aliasing & Digital Master Filter boundaries (44.1 kHz Redbook CD)
STUDIO_FILTER_MIN_HZ   = 21_000.0   # 21.0 kHz threshold for studio anti-aliasing / Nyquist filter
STUDIO_FILTER_MAX_HZ   = 22_050.0   # 44.1 kHz Nyquist limit
DIGITAL_MASTER_MIN_HZ  = 20_000.0   # 20.0 kHz boundary for studio digital mastering filters

# Minimum drop across transition window to qualify as a brickwall cutoff
# Note: True lossless has max 1000 Hz drop < 1.3 dB; lossy cutoffs drop 10–30 dB.
BRICKWALL_MIN_DROP_DB      = 8.0    # Drop in 1000 Hz window (slope >= 8 dB/kHz)
BRICKWALL_WIDE_DROP_DB     = 11.0   # Drop in 1600 Hz window (slope >= 6.8 dB/kHz)
BRICKWALL_MIN_SLOPE_DB_PER_KHZ = -20.0  # Steepness requirement to avoid gentle acoustic roll-off

# Stopband attenuation requirements
STOPBAND_MAX_ENERGY_DB     = -60.0  # Energy above cutoff must be below this level (dBFS)
STOPBAND_PASSBAND_DELTA_DB = 8.0    # Energy above cutoff must be at least this much lower than passband
STOPBAND_MAX_STD_DB        = 12.0   # Stopband variance tolerance (permits dither and transient residual)

# Encoder fingerprint bands (Hz)
ENCODER_BANDS = [
    (14_000, 16_800, "MP3 ~128 kbps / YouTube AAC / Vorbis"),
    (16_800, 19_500, "MP3 ~192–256 kbps / AAC 192 kbps"),
    (19_500, 20_000, "MP3 ~320 kbps (LAME) / Opus 160+ kbps"),
    (20_000, 21_000, "Studio Digital Master Filter (Mora / Digital Master)"),
    (21_000, float("inf"), "Studio Anti-Aliasing Filter (Redbook CD)"),
]

# ── Anti-spoof detection ─────────────────────────────────────────────────────
HOLE_BAND_LOW_HZ  = 12_000.0
HOLE_BAND_HIGH_HZ = 15_800.0
HOLE_DROP_DB      = 35.0
HOLE_RATIO_THRESH = 0.38        # R_hole > this → SPECTRAL_HOLES_DETECTED

MID_BAND_LOW_HZ  =  3_000.0
MID_BAND_HIGH_HZ =  8_000.0
HF_BAND_LOW_HZ   = 16_500.0
HF_BAND_HIGH_HZ  = 21_500.0

CORRELATION_THRESH      = 0.12   # r < this → suspicion
HF_STDEV_THRESH_DB      = 2.5    # σ_high < this → stationary noise
HF_ENERGY_FLOOR_DB      = -90.0  # above this means HF energy exists

# ── Hi-Res / DSD ultrasonic ──────────────────────────────────────────────────
HIRES_SAMPLE_RATE_THRESHOLD = 88_200   # ≥ this = Hi-Res
UPSAMPLED_DROP_DB           = 30.0     # brickwall at 22.05 / 24 kHz boundary

DSD_AUDIBLE_LOW_HZ  =  4_000.0
DSD_AUDIBLE_HIGH_HZ = 12_000.0
DSD_ULTRA_LOW_HZ    = 23_000.0
DSD_ULTRA_HIGH_HZ   = 36_000.0
DSD_ULTRA_CORR_THRESH = 0.08

# ── Scoring matrix ───────────────────────────────────────────────────────────
BASE_SCORE = 100

SCORE_DEDUCTIONS = {
    "brickwall_low":    60,   # fc ≤ 16 800 Hz (Severe lossy MP3 128k / YouTube)
    "brickwall_mid":    45,   # 16 800 < fc ≤ 19 500 Hz (MP3 192–256k / AAC)
    "brickwall_high":   25,   # 19 500 < fc ≤ 20 700 Hz (MP3 320k / Opus)
    "fake_noise":       65,   # Stationary synthetic HF noise injected
    "spectral_holes":   25,   # MDCT spectral holes
    "bit_padded":       30,   # 16-bit padded to 24-bit container
    "fake_hires":       40,   # Upsampled Hi-Res with CD Nyquist brickwall
    "ai_artifacts":     35,   # AI / Neural vocoder bandwidth extension
    "module_b_knee":    15,   # Soft anomaly: slope knee discontinuity
    "natural_rolloff":  10,   # Soft anomaly: gradual natural roll-off without brickwall
}

# Verdict thresholds
VERDICT_AUTHENTIC   = 85
VERDICT_SUSPICIOUS  = 60
