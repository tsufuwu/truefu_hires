"""
core/spectrogram.py — Headless Matplotlib spectrogram renderer.

Renders a 1200×500 px dark-mode spectrogram (inferno colormap, -120 to 0 dBFS)
with an annotated cyan dashed line at the detected cutoff frequency.
Returns a data-URI base64 PNG string.
"""
from __future__ import annotations

import base64
import io
import logging
from typing import Optional

import matplotlib
matplotlib.use("Agg")  # headless / non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
from scipy import signal as sp_signal

from config import STFT_NOVERLAP_HIGH, STFT_NOVERLAP_LOW, STFT_NPERSEG_HIGH, STFT_NPERSEG_LOW

logger = logging.getLogger(__name__)

# Dark-mode style
DARK_BG   = "#0d0d14"
GRID_CLR  = "#1e1e2e"
TEXT_CLR  = "#c0c0d0"
CYAN_CLR  = "#00e5ff"

SPEC_VMIN = -120.0  # dBFS minimum (noise floor)
SPEC_VMAX =    0.0  # dBFS maximum (full scale)


def render_spectrogram(
    float32_mono: np.ndarray,
    sample_rate: int,
    detected_cutoff_hz: Optional[float] = None,
    width_px: int = 1200,
    height_px: int = 500,
    dpi: int = 100,
) -> str:
    """
    Render a spectrogram PNG and return as a base64-encoded data-URI string.

    Args:
        float32_mono       : normalised [-1, 1] mono audio
        sample_rate        : Hz
        detected_cutoff_hz : if provided, draw an annotated cutoff line
        width_px / height_px / dpi: output dimensions

    Returns:
        "data:image/png;base64,<base64-string>"
    """
    if float32_mono.size == 0:
        return ""

    # ── STFT ─────────────────────────────────────────────────────────────────
    if sample_rate <= 48_000:
        nperseg, noverlap = STFT_NPERSEG_LOW, STFT_NOVERLAP_LOW
    else:
        nperseg, noverlap = STFT_NPERSEG_HIGH, STFT_NOVERLAP_HIGH

    nperseg  = min(nperseg, len(float32_mono))
    noverlap = min(noverlap, nperseg - 1)

    freqs, times, Zxx = sp_signal.stft(
        float32_mono, fs=sample_rate,
        window="hann", nperseg=nperseg, noverlap=noverlap,
    )
    magnitude_db = 20.0 * np.log10(np.maximum(np.abs(Zxx), 1e-7))

    # ── Figure ───────────────────────────────────────────────────────────────
    fig_w = width_px / dpi
    fig_h = height_px / dpi
    fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=dpi)
    fig.patch.set_facecolor(DARK_BG)
    ax.set_facecolor(DARK_BG)

    # Plot (transpose so time is x-axis, frequency is y-axis)
    img = ax.imshow(
        magnitude_db,
        origin="lower",
        aspect="auto",
        extent=[times[0], times[-1], freqs[0] / 1000.0, freqs[-1] / 1000.0],
        cmap="inferno",
        vmin=SPEC_VMIN,
        vmax=SPEC_VMAX,
        interpolation="bilinear",
    )

    # Colourbar
    cbar = fig.colorbar(img, ax=ax, pad=0.01, fraction=0.02)
    cbar.set_label("dBFS", color=TEXT_CLR, fontsize=9)
    cbar.ax.yaxis.set_tick_params(color=TEXT_CLR)
    plt.setp(plt.getp(cbar.ax.axes, "yticklabels"), color=TEXT_CLR)

    # ── Cutoff annotation ────────────────────────────────────────────────────
    if detected_cutoff_hz is not None:
        cutoff_khz = detected_cutoff_hz / 1000.0
        ax.axhline(y=cutoff_khz, color=CYAN_CLR, linewidth=1.5, linestyle="--", alpha=0.9)
        ax.text(
            times[-1] * 0.02,
            cutoff_khz + 0.3,
            f"Detected Cutoff: {cutoff_khz:.1f} kHz",
            color=CYAN_CLR,
            fontsize=8,
            fontweight="bold",
            va="bottom",
        )

    # ── Labels & styling ─────────────────────────────────────────────────────
    ax.set_xlabel("Time (s)", color=TEXT_CLR, fontsize=9)
    ax.set_ylabel("Frequency (kHz)", color=TEXT_CLR, fontsize=9)
    ax.tick_params(colors=TEXT_CLR, labelsize=8)
    ax.spines["bottom"].set_color(GRID_CLR)
    ax.spines["left"].set_color(GRID_CLR)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.yaxis.set_major_formatter(ticker.FormatStrFormatter("%.0f"))
    ax.grid(False)

    plt.tight_layout(pad=0.5)

    # ── Encode to base64 ─────────────────────────────────────────────────────
    buf = io.BytesIO()
    fig.savefig(buf, format="png", facecolor=DARK_BG, dpi=dpi)
    plt.close(fig)
    buf.seek(0)
    encoded = base64.b64encode(buf.read()).decode("ascii")
    return f"data:image/png;base64,{encoded}"
