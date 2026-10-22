"""
core/scorer.py — Heuristic decision tree & Authenticity Score (0–100).

Deduction table (from config.py SCORE_DEDUCTIONS):
  brickwall_low   (fc ≤ 16 800)  → -75  → FAKE_UPSCALED
  brickwall_mid   (fc ≤ 19 500)  → -65  → FAKE_UPSCALED
  brickwall_high  (fc ≤ 20 700)  → -50  → SUSPICIOUS_TRANSCODE
  fake_noise                     → -80  → FAKE_SPOOFED
  spectral_holes                 → -35  → (confirms lossy MDCT)
  bit_padded                     → -30  → FAKE_BIT_DEPTH
  fake_hires                     → -40  → UPSAMPLED_HIRES
  natural_rolloff                → -10  → AUTHENTIC_WITH_NOTE

Final verdicts:
  85–100 → AUTHENTIC_LOSSLESS  (green)
  55–84  → SUSPICIOUS           (amber)
   0–54  → FAKE_UPSCALED / …   (red)
"""
from __future__ import annotations

from typing import Optional

from config import (
    BASE_SCORE,
    SCORE_DEDUCTIONS,
    VERDICT_AUTHENTIC,
    VERDICT_SUSPICIOUS,
)
from schemas import (
    AdvancedModulesSchema,
    AntiSpoofSchema,
    BitDepthSchema,
    SpectralCutoffSchema,
    UltrasonicSchema,
    VerdictSchema,
)


def score_and_verdict(
    bit_depth: BitDepthSchema,
    spectral: SpectralCutoffSchema,
    anti_spoof: AntiSpoofSchema,
    ultrasonic: UltrasonicSchema,
    advanced: Optional[AdvancedModulesSchema] = None,
) -> VerdictSchema:
    # ── Override if AccurateRip confirms 100% CD bit-perfect match ──────────
    if advanced and advanced.accuraterip.db_status == "CONFIRMED_BIT_PERFECT":
        return VerdictSchema(
            score=100,
            status="AUTHENTIC_LOSSLESS",
            label="Authentic CD Master (AccurateRip Bit-Perfect Confirmed)",
            confidence="HIGH",
            summary=advanced.accuraterip.detail,
        )

    score = BASE_SCORE
    hard_evidences: list[str] = []
    soft_anomalies: list[str] = []
    flags: list[str] = []
    deductions: list[str] = []

    fc = spectral.detected_cutoff_hz
    # Cross-validation guard: Cutoff at >= 20.0 kHz with clean MDCT (< 4% holes)
    # is an authentic Studio Digital Master Filter (e.g. Mora/Apple Music/J-Rock mastering)
    is_digital_master = (
        fc is not None
        and fc >= 20_000.0
        and anti_spoof.spectral_holes_ratio < 0.04
        and not anti_spoof.holes_detected
    )
    if is_digital_master:
        spectral.is_studio_filter = True
        spectral.is_brickwall = False

    is_lossy_brickwall = spectral.is_brickwall and not getattr(spectral, "is_studio_filter", False)

    # ── 1. HARD EVIDENCE EVALUATION (Bằng chứng thép) ─────────────────────────

    # A. Brickwall cutoffs
    if fc is not None and is_lossy_brickwall:
        if fc <= 16_800:
            score -= SCORE_DEDUCTIONS["brickwall_low"]
            flags.append("FAKE_UPSCALED")
            hard_evidences.append("brickwall_low")
            deductions.append(
                f"Severe brickwall cutoff at {fc/1000:.2f} kHz (<=16.8 kHz): likely MP3 128k/YouTube transcode (-{SCORE_DEDUCTIONS['brickwall_low']})"
            )
        elif fc <= 19_500:
            score -= SCORE_DEDUCTIONS["brickwall_mid"]
            flags.append("FAKE_UPSCALED")
            hard_evidences.append("brickwall_mid")
            deductions.append(
                f"Brickwall cutoff at {fc/1000:.2f} kHz (16.8-19.5 kHz): likely MP3 192-256k/AAC transcode (-{SCORE_DEDUCTIONS['brickwall_mid']})"
            )
        elif fc <= 20_700:
            score -= SCORE_DEDUCTIONS["brickwall_high"]
            flags.append("SUSPICIOUS_TRANSCODE")
            hard_evidences.append("brickwall_high")
            deductions.append(
                f"High-frequency cutoff at {fc/1000:.2f} kHz (19.5-20.7 kHz): likely MP3 320k/Opus (-{SCORE_DEDUCTIONS['brickwall_high']})"
            )

    # B. Fake noise injection & stealth noise layer
    if anti_spoof.fake_noise_injected:
        score -= SCORE_DEDUCTIONS["fake_noise"]
        flags.append("FAKE_SPOOFED")
        hard_evidences.append("fake_noise")
        deductions.append(
            f"Stationary synthetic HF noise injected to spoof spectrum (-{SCORE_DEDUCTIONS['fake_noise']})"
        )
    elif advanced and advanced.phase_coherence.is_stealth_noise_layer:
        score -= SCORE_DEDUCTIONS["fake_noise"]
        flags.append("FAKE_SPOOFED")
        hard_evidences.append("stealth_noise")
        deductions.append(
            f"Stealth flat noise layer / missing HF transient coherence (sigma={advanced.phase_coherence.hf_time_variance_db:.1f} dB) (-{SCORE_DEDUCTIONS['fake_noise']})"
        )

    # C. Bit padding & Fake bit-depth in lossy containers
    if bit_depth.is_padded:
        score -= SCORE_DEDUCTIONS["bit_padded"]
        flags.append("FAKE_BIT_DEPTH")
        hard_evidences.append("bit_padded")
        deductions.append(
            f"16-bit audio padded to {bit_depth.declared}-bit container (-{SCORE_DEDUCTIONS['bit_padded']})"
        )
    elif is_lossy_brickwall and bit_depth.declared >= 24:
        score -= SCORE_DEDUCTIONS["bit_padded"]
        flags.append("FAKE_BIT_DEPTH")
        hard_evidences.append("lossy_in_24bit")
        fc_str = f" at {fc/1000:.1f} kHz" if fc else ""
        deductions.append(
            f"Declared {bit_depth.declared}-bit container contains lossy audio with cutoff{fc_str} (-{SCORE_DEDUCTIONS['bit_padded']})"
        )
    elif bit_depth.suspicious_scaling:
        score -= SCORE_DEDUCTIONS["bit_padded"]
        flags.append("FAKE_BIT_DEPTH")
        hard_evidences.append("suspicious_bit_scaling")
        deductions.append(
            f"Suspicious bit scaling: bottom bits lack entropy for genuine {bit_depth.declared}-bit master (-{SCORE_DEDUCTIONS['bit_padded']})"
        )

    # D. Fake Hi-Res upsampling
    if ultrasonic.applicable and ultrasonic.fake_hires_upsampled:
        score -= SCORE_DEDUCTIONS["fake_hires"]
        flags.append("UPSAMPLED_HIRES")
        hard_evidences.append("fake_hires")
        deductions.append(
            f"Brickwall cutoff at CD boundary (22.05 kHz) in Hi-Res container (-{SCORE_DEDUCTIONS['fake_hires']})"
        )

    # E. AI / Neural Vocoder bandwidth extension
    if advanced and advanced.ai_artifacts.ai_artifacts_detected:
        score -= SCORE_DEDUCTIONS["ai_artifacts"]
        flags.append("FAKE_AI_UPSCALED")
        hard_evidences.append("ai_artifacts")
        deductions.append(
            f"AI / Neural Vocoder artifacts detected (phase jitter {advanced.ai_artifacts.phase_jitter_entropy:.2f}, comb ripple {advanced.ai_artifacts.comb_ripple_db:.1f} dB) (-{SCORE_DEDUCTIONS['ai_artifacts']})"
        )

    # F. Spectral holes (MDCT codec quantization)
    if anti_spoof.holes_detected:
        score -= SCORE_DEDUCTIONS["spectral_holes"]
        flags.append("SUSPICIOUS")
        hard_evidences.append("spectral_holes")
        deductions.append(
            f"MDCT spectral holes in 12–16 kHz band (ratio {anti_spoof.spectral_holes_ratio:.3f}) (-{SCORE_DEDUCTIONS['spectral_holes']})"
        )

    # ── 2. SOFT ANOMALIES & MASTERING QUIRKS (Cảnh báo nhẹ / Đặc thù bản phối) ─

    # G. Module B: Natural decay slope knee
    if advanced and advanced.natural_decay.violates_natural_decay:
        # Cross-validation guard: if Pillar 2 confirms Studio Filter (>= 21.5 kHz)
        if spectral.is_studio_filter or (fc and fc >= 21_500 and not spectral.is_brickwall):
            advanced.natural_decay.violates_natural_decay = False
            advanced.natural_decay.status = "PASSED"
        else:
            # Soft penalty: proportional warning (15 points), NEVER a kill switch
            knee_pen = SCORE_DEDUCTIONS.get("module_b_knee", 15)
            score -= knee_pen
            soft_anomalies.append("natural_decay_knee")
            flags.append("SUSPICIOUS_ANOMALY")
            knee_str = (
                f" at {advanced.natural_decay.knee_frequency_khz:.1f} kHz"
                if advanced.natural_decay.knee_frequency_khz
                else ""
            )
            deductions.append(
                f"Slope knee discontinuity{knee_str} transitioning to flat shelf (-{knee_pen})"
            )

    # H. Natural roll-off without brickwall
    natural_rolloff = (
        not is_lossy_brickwall
        and not getattr(spectral, "is_studio_filter", False)
        and anti_spoof.spectral_holes_ratio < 0.15
        and (
            fc is None
            or (spectral.rolloff_slope_db_per_khz is not None and abs(spectral.rolloff_slope_db_per_khz) < 20)
        )
        and not any(f in ("FAKE_UPSCALED", "FAKE_SPOOFED", "FAKE_BIT_DEPTH", "FAKE_AI_UPSCALED") for f in flags)
    )
    if natural_rolloff and not is_lossy_brickwall:
        if (fc or 0) > 0 and (fc or 22050) < 18_000:
            score -= SCORE_DEDUCTIONS["natural_rolloff"]
            soft_anomalies.append("natural_rolloff")
            deductions.append(
                f"Gradual acoustic roll-off below 18 kHz (-{SCORE_DEDUCTIONS['natural_rolloff']})"
            )

    # ── 3. CONSENSUS ENGINE & GUARDRAIL VETO RULES (Quy tắc phủ quyết) ────────

    # VETO RULE 1: Soft anomalies alone CANNOT brand a file as FAKE (< 60).
    # If there is NO hard evidence, the score is capped to never drop below 60.
    if len(hard_evidences) == 0:
        score = max(60, min(100, score))
        flags = [f for f in flags if not f.startswith("FAKE_")]

    # VETO RULE 2: A file can only be declared FAKE (< 60) if:
    # 1. It has severe hard evidence (severe cutoff <=19.5k, fake noise, bit padding, fake hires, AI vocoder); OR
    # 2. It has consensus from at least 2 distinct anomalies/evidences.
    # Single moderate evidence alone (e.g. only brickwall_high at 20.2k, or only MDCT holes) stays in SUSPICIOUS (60–84).
    severe_evidences = {
        "brickwall_low",
        "brickwall_mid",
        "fake_noise",
        "stealth_noise",
        "bit_padded",
        "lossy_in_24bit",
        "fake_hires",
        "ai_artifacts",
    }
    has_severe = any(e in severe_evidences for e in hard_evidences)
    total_anomalies = len(hard_evidences) + len(soft_anomalies)

    if not has_severe and total_anomalies < 2:
        score = max(60, min(100, score))
        flags = [f for f in flags if not f.startswith("FAKE_")]

    score = max(0, min(100, score))

    # ── 4. FOUR-TIER STATUS & LABEL ASSIGNMENT ───────────────────────────────
    # Tier 1: 85–100 → AUTHENTIC_LOSSLESS
    # Tier 2: 60–84  → SUSPICIOUS / SUSPICIOUS_ANOMALY / SUSPICIOUS_TRANSCODE
    # Tier 3:  0–59  → FAKE_UPSCALED / FAKE_SPOOFED / FAKE_BIT_DEPTH / UPSAMPLED_HIRES
    if score >= VERDICT_AUTHENTIC:
        status = "AUTHENTIC_LOSSLESS"
        label = "Authentic Lossless"
        confidence = "HIGH" if score >= 90 else "MEDIUM"
    elif score >= VERDICT_SUSPICIOUS:
        # 60–84: Suspicious / Anomaly
        if "SUSPICIOUS_TRANSCODE" in flags:
            status = "SUSPICIOUS_TRANSCODE"
        elif "SUSPICIOUS_ANOMALY" in flags or "natural_decay_knee" in soft_anomalies:
            status = "SUSPICIOUS_ANOMALY"
        elif "FAKE_BIT_DEPTH" in flags:
            status = "FAKE_BIT_DEPTH"
        else:
            status = flags[0] if flags else "SUSPICIOUS"
        label = _make_label(status, fc, anti_spoof)
        confidence = "MEDIUM"
    else:
        # 0–59: Confirmed Fake / Transcode
        status = flags[0] if flags else "FAKE_UPSCALED"
        label = _make_label(status, fc, anti_spoof)
        confidence = "HIGH" if score <= 40 else "MEDIUM"

    # ── 5. SUMMARY GENERATION ────────────────────────────────────────────────
    if deductions:
        summary_body = "; ".join(deductions)
        if 60 <= score < VERDICT_AUTHENTIC:
            summary = (
                f"Issues detected: {summary_body}. "
                "Notice: Unusual frequency characteristics detected, possibly a mastering quirk or mild compression. "
                "Critical listening or comparison recommended."
            )
        else:
            summary = f"Issues detected: {summary_body}."
    else:
        summary = (
            "No anomalies detected. Full-spectrum lossless audio with "
            "genuine bit-depth confirmed."
        )

    return VerdictSchema(
        score=score,
        status=status,
        label=label,
        confidence=confidence,
        summary=summary,
    )


def _make_label(
    status: str,
    fc: Optional[float],
    anti_spoof: AntiSpoofSchema,
) -> str:
    if status == "SUSPICIOUS_ANOMALY":
        return "Suspicious / Mastering Anomaly (Unusual Roll-Off Characteristic)"
    if status == "FAKE_UPSCALED":
        if fc:
            return f"Fake Lossless (Transcoded from lossy source, cutoff {fc/1000:.2f} kHz)"
        return "Fake Lossless (Transcoded from lossy source)"
    if status == "FAKE_SPOOFED":
        return "Fake Lossless (Lossy + Synthetic HF Noise Injection)"
    if status == "FAKE_AI_UPSCALED":
        return "Fake Lossless (AI / Neural Bandwidth Extension Artifacts Detected)"
    if status == "FAKE_BIT_DEPTH":
        return "Fake Bit-Depth (Inflated 24-bit container from lossy or 16-bit source)"
    if status == "SUSPICIOUS_TRANSCODE":
        return f"Suspicious (Possible MP3 320k / Opus transcode, cutoff {fc/1000:.2f} kHz)" if fc else "Suspicious Transcode"
    if status == "UPSAMPLED_HIRES":
        return "Upsampled Hi-Res (Standard Redbook audio in Hi-Res container)"
    if status == "SUSPICIOUS":
        return "Suspicious / Cannot Fully Confirm Authenticity"
    return status

