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
    # ── Rule 3: Phân biệt Bộ lọc Phòng thu (Digital Master / Pipeline Filter) ở ngưỡng 20.0 – 22.05 kHz ──
    # Nếu cutoff_freq >= 20.0 kHz VÀ mdct_hole_ratio < 0.10 (Sạch, không có lỗ nén) VÀ bit_depth đạt chuẩn:
    # -> Phân loại là: "Giới hạn tần số từ bản gốc phòng thu (Studio Master / 44.1kHz Pipeline Filter)"
    # -> Không đánh rớt xuống "Lossless Giả". Giữ điểm số tổng ở mức Đạt chuẩn / Khả quan (>= 80 điểm).
    is_authentic_bits = (
        not bit_depth.is_padded
        and not bit_depth.suspicious_scaling
        and bit_depth.effective >= 16
    )
    is_clean_mdct = (
        anti_spoof.spectral_holes_ratio < 0.10
        and not anti_spoof.holes_detected
    )
    is_studio_pipeline_filter = (
        fc is not None
        and fc >= 20_000.0
        and is_clean_mdct
        and is_authentic_bits
    )

    if is_studio_pipeline_filter:
        spectral.is_studio_filter = True
        spectral.is_brickwall = False
        slope_val = spectral.rolloff_slope_db_per_khz or 0.0
        if fc and fc >= 21_000.0:
            spectral.suspected_source_encoder = "Studio Anti-Aliasing Filter (Redbook CD)"
            spectral.detail = (
                f"Studio anti-aliasing filter detected at {fc/1000:.2f} kHz "
                f"(slope {slope_val:.1f} dB/kHz) near Nyquist boundary. "
                "Preserves genuine Redbook CD audio bandwidth."
            )
        else:
            spectral.suspected_source_encoder = "Giới hạn tần số từ bản gốc phòng thu (Studio Master / 44.1kHz Pipeline Filter)"
            spectral.detail = (
                f"Giới hạn tần số từ bản gốc phòng thu (Studio Master / 44.1kHz Pipeline Filter) phát hiện tại {fc/1000:.2f} kHz "
                f"(độ dốc {abs(slope_val):.1f} dB/kHz). Tỷ lệ lỗ nén MDCT sạch ({anti_spoof.spectral_holes_ratio:.1%}) "
                f"và độ sâu bit đạt chuẩn ({bit_depth.effective}-bit). Toàn bộ dải phổ âm thanh nguyên bản phòng thu được bảo toàn."
            )

    is_lossy_brickwall = spectral.is_brickwall and not getattr(spectral, "is_studio_filter", False)

    # ── 1. HARD EVIDENCE EVALUATION (Bằng chứng thép) ─────────────────────────

    # A. Brickwall cutoffs & 3-Tier Segmentation
    if fc is not None and is_lossy_brickwall:
        active_ratio = getattr(spectral, "active_cutoff_ratio", None) or 0.0
        std_khz = getattr(spectral, "cutoff_std_khz", None)
        if std_khz is None:
            std_khz = 1.0
        pre_energy = getattr(spectral, "pre_cutoff_energy_db", None)
        if pre_energy is None:
            pre_energy = -100.0
        slope_val = spectral.rolloff_slope_db_per_khz or 0.0
        hf_energy_14_20 = getattr(spectral, "hf_energy_14_20_db", None)
        if hf_energy_14_20 is None:
            hf_energy_14_20 = -100.0

        is_strict_clean_mdct = (anti_spoof.spectral_holes_ratio <= 0.01 and not anti_spoof.holes_detected)

        # ── PHÂN KHÚC 1: fc <= 17.5 kHz (Vùng nguy hiểm của MP3 128k / YouTube AAC 128k) ──
        if fc <= 17_500.0:
            # Trường hợp 1A: Cắt cụt nhân tạo (Hard Brickwall)
            is_hard_brickwall_128k = (
                active_ratio >= 0.25
                or std_khz < 0.40
                or (slope_val <= -25.0 and pre_energy > -60.0)
            )

            # Trường hợp 1B: Nhạc mộc thưa thực sự (rất ít âm cao, năng lượng dải 10-16k cực thấp)
            is_sparse_acoustic_128k = (
                active_ratio < 0.15
                and (pre_energy < -75.0 or hf_energy_14_20 < -75.0)
                and is_strict_clean_mdct
            )

            if is_hard_brickwall_128k:
                # BẤT CHẤP MDCT Holes == 0% và Bit Depth == 24-bit:
                # BẮT BUỘC kết luận: Lossless Giả (Transcoded từ nguồn Lossy ~128kbps / YouTube AAC) với Độ tin cậy cao
                score -= 68
                flags.append("FAKE_UPSCALED_128K")
                hard_evidences.append("brickwall_low_hard")
                deductions.append(
                    f"Cắt cụt nhân tạo (Hard Brickwall) tại {fc/1000:.2f} kHz "
                    f"(mật độ chạm trần {active_ratio:.1%}, độ tản mác đỉnh {std_khz:.2f} kHz, dốc {slope_val:.1f} dB/kHz): "
                    f"đặc trưng nguồn Lossy ~128kbps / YouTube AAC (-68)"
                )
            elif is_sparse_acoustic_128k:
                score -= 20
                flags.append("SUSPICIOUS_BANDWIDTH_LIMIT")
                soft_anomalies.append("isolated_bandwidth_limit")
                deductions.append(
                    f"Nghi vấn giới hạn băng thông tại {fc/1000:.1f} kHz "
                    f"(bản phối mộc ít âm cao, năng lượng dải cao rất thấp {pre_energy:.1f} dBFS) (-20)"
                )
            else:
                score -= 65
                flags.append("FAKE_UPSCALED")
                hard_evidences.append("brickwall_low")
                deductions.append(
                    f"Severe brickwall cutoff at {fc/1000:.2f} kHz (<=17.5 kHz): likely MP3 128k/YouTube transcode (-65)"
                )

        # ── PHÂN KHÚC 2: 17.5 kHz < fc < 20.0 kHz (Vùng MP3 192–256k / Vorbis / AAC 192k) ──
        elif fc < 20_000.0:
            is_hard_brickwall_mid = (
                (active_ratio >= 0.30 and std_khz < 0.35)
                or (anti_spoof.spectral_holes_ratio > 0.05)
                or anti_spoof.holes_detected
            )
            is_acoustic_undulation_mid = (
                std_khz >= 0.50
                and is_strict_clean_mdct
            )

            if is_hard_brickwall_mid:
                score -= 55
                flags.append("FAKE_UPSCALED")
                hard_evidences.append("brickwall_mid")
                deductions.append(
                    f"Vết cắt dốc đứng (Hard Brickwall) tại {fc/1000:.2f} kHz "
                    f"(chạm trần {active_ratio:.1%}, tản mác {std_khz:.2f} kHz): "
                    f"đặc trưng nén Lossy 192–256kbps (-55)"
                )
            elif is_acoustic_undulation_mid:
                score -= 15
                flags.append("SUSPICIOUS_ACOUSTIC_LIMIT")
                soft_anomalies.append("acoustic_sparse_limit")
                deductions.append(
                    f"Giới hạn âm học tự nhiên tại {fc/1000:.1f} kHz "
                    f"(đỉnh phổ nhấp nhô tự nhiên std={std_khz:.2f} kHz, sạch lỗ nén MDCT) (-15)"
                )
            else:
                score -= 50
                flags.append("SUSPICIOUS_TRANSCODE")
                hard_evidences.append("brickwall_mid")
                deductions.append(
                    f"Brickwall cutoff at {fc/1000:.2f} kHz: likely MP3 192-256k/AAC transcode (-50)"
                )

        # ── PHÂN KHÚC 3: fc >= 20.0 kHz ──
        # Đã được xử lý ở Rule 3 (Studio Master / Digital Master Filter) bên trên,
        # nếu lọt xuống đây thì là brickwall thông thường ở dải siêu cao
        else:
            score -= SCORE_DEDUCTIONS.get("brickwall_high", 50)
            flags.append("SUSPICIOUS_TRANSCODE")
            hard_evidences.append("brickwall_high")
            deductions.append(
                f"High-frequency cutoff at {fc/1000:.2f} kHz: likely MP3 320k/Opus (-{SCORE_DEDUCTIONS.get('brickwall_high', 50)})"
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

    # C. Bit padding & Fake bit-depth
    # Tách biệt rạch ròi: Module Độ Sâu Bit chỉ được phép kết luận dựa trên dữ liệu bit thực tế (LSB bit-histograms)
    # Tuyệt đối không gắn nhãn FAKE_BIT_DEPTH khi số bit bị chèn bằng 0.
    if bit_depth.is_padded:
        score -= SCORE_DEDUCTIONS["bit_padded"]
        flags.append("FAKE_BIT_DEPTH")
        hard_evidences.append("bit_padded")
        deductions.append(
            f"16-bit audio padded to {bit_depth.declared}-bit container (-{SCORE_DEDUCTIONS['bit_padded']})"
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
        "brickwall_low_hard",
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
    # Rule 7: Đồng bộ Logic Kết Luận Tổng (Final Verdict & Confidence Score)
    only_cutoff_evidence = (
        len(hard_evidences) == 1
        and any(e in ("brickwall_low", "brickwall_mid", "brickwall_high") for e in hard_evidences)
        and (anti_spoof.spectral_holes_ratio <= 0.01 and not anti_spoof.holes_detected)
        and (not bit_depth.is_padded and not bit_depth.suspicious_scaling)
    )

    if "FAKE_UPSCALED_128K" in flags or "brickwall_low_hard" in hard_evidences:
        status = "FAKE_UPSCALED"
        label = f"Fake Lossless (Transcoded từ nguồn Lossy ~128kbps / YouTube AAC, cutoff {fc/1000:.2f} kHz)" if fc else "Fake Lossless (Transcoded từ nguồn Lossy ~128kbps / YouTube AAC)"
        confidence = "HIGH"
    elif score >= VERDICT_AUTHENTIC:
        status = "AUTHENTIC_LOSSLESS"
        label = "Authentic Lossless"
        confidence = "HIGH" if score >= 90 else "MEDIUM"
    elif score >= VERDICT_SUSPICIOUS:
        # 60–84: Suspicious / Anomaly (Màu vàng)
        if "SUSPICIOUS_ACOUSTIC_LIMIT" in flags:
            status = "SUSPICIOUS_ACOUSTIC_LIMIT"
        elif "SUSPICIOUS_BANDWIDTH_LIMIT" in flags:
            status = "SUSPICIOUS_BANDWIDTH_LIMIT"
        elif "SUSPICIOUS_TRANSCODE" in flags:
            status = "SUSPICIOUS_TRANSCODE"
        elif "SUSPICIOUS_ANOMALY" in flags or "natural_decay_knee" in soft_anomalies:
            status = "SUSPICIOUS_ANOMALY"
        elif "FAKE_BIT_DEPTH" in flags:
            status = "FAKE_BIT_DEPTH"
        else:
            status = flags[0] if flags else "SUSPICIOUS"
        label = _make_label(status, fc, anti_spoof)
        confidence = "LOW" if only_cutoff_evidence else "MEDIUM"
    else:
        # 0–59: Confirmed Fake / Transcode
        status = flags[0] if flags else "FAKE_UPSCALED"
        if status == "FAKE_UPSCALED_128K":
            status = "FAKE_UPSCALED"
        label = _make_label(status, fc, anti_spoof)
        if "brickwall_low_hard" in hard_evidences:
            confidence = "HIGH"
        elif only_cutoff_evidence:
            confidence = "MEDIUM"
        else:
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
    if status == "SUSPICIOUS_BANDWIDTH_LIMIT":
        return f"Nghi vấn giới hạn băng thông ({fc/1000:.1f} kHz) / Bản phối mộc ít âm cao" if fc else "Nghi vấn giới hạn băng thông / Bản phối mộc ít âm cao"
    if status == "SUSPICIOUS_ACOUSTIC_LIMIT":
        return "Giới hạn âm học tự nhiên (Bản phối ít nhạc cụ dải cao)"
    if status == "FAKE_UPSCALED_128K":
        return f"Fake Lossless (Transcoded từ nguồn Lossy ~128kbps / YouTube AAC, cutoff {fc/1000:.2f} kHz)" if fc else "Fake Lossless (Transcoded từ nguồn Lossy ~128kbps / YouTube AAC)"
    if status == "FAKE_UPSCALED":
        if fc and fc <= 17_500:
            return f"Fake Lossless (Transcoded từ nguồn Lossy ~128kbps / YouTube AAC, cutoff {fc/1000:.2f} kHz)"
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

