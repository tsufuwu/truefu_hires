// utils/localize.ts — Comprehensive Vietnamese and English text localization for all DSP diagnostics
import type { BitDepthData, SpectralCutoffData, AntiSpoofData, UltrasonicData, VerdictData } from '../api';
import type { Language } from '../i18n';

/**
 * Localize the suspected encoder label
 */
export function localizeEncoder(encoder: string | null | undefined, lang: Language): string {
  if (!encoder) return lang === 'vi' ? 'Chưa xác định' : 'Unknown encoder';
  if (lang === 'en') return encoder;

  if (encoder.includes('Digital Master')) {
    return 'Bộ lọc phòng thu kỹ thuật số (Digital Master Filter)';
  }
  if (encoder.includes('Studio Anti-Aliasing Filter') || encoder.includes('Studio')) {
    return 'Bộ lọc chống dội âm chuẩn phòng thu (Studio Anti-Aliasing Filter)';
  }
  if (encoder.includes('128 kbps')) {
    return 'MP3 ~128 kbps / YouTube AAC / Ogg Vorbis';
  }
  if (encoder.includes('192')) {
    return 'MP3 ~192–256 kbps / AAC 192 kbps';
  }
  if (encoder.includes('320')) {
    return 'MP3 ~320 kbps (LAME) / Opus 160+ kbps';
  }
  if (encoder.includes('Redbook')) {
    return 'Băng thông đĩa CD Redbook (44.1 kHz)';
  }
  return encoder;
}

/**
 * Localize Pillar 1: Bit Depth detail string
 */
export function localizeBitDepthDetail(
  data: BitDepthData,
  spectral: SpectralCutoffData,
  lang: Language
): string {
  if (lang === 'en') {
    return data.detail;
  }

  // Vietnamese localization:
  if (data.suspicious_scaling && spectral.is_brickwall && !spectral.is_studio_filter) {
    const fc = spectral.detected_cutoff_hz ? (spectral.detected_cutoff_hz / 1000).toFixed(1) : '16';
    return `Tệp khai báo container ${data.declared}-bit, nhưng phổ tần bị cắt cụt brickwall tại ${fc} kHz đặc trưng của nguồn nén lossy (MP3/AAC). Các bit thấp thực chất là nhiễu dither/độn giả lập, không phải độ động 24-bit thực tế.`;
  }

  if (data.is_padded) {
    return `Các bit thấp LSB cố định bằng 0. Tệp âm thanh thực tế chỉ là ${data.effective}-bit bị chèn thêm ${data.wasted_bits} bit 0 để giả mạo thành container ${data.declared}-bit.`;
  }

  if (data.suspicious_scaling) {
    return `Khai báo ${data.declared}-bit, thực tế ${data.effective}-bit. Các bit thấp có độ biến thiên quá ít — nghi vấn âm thanh 16-bit bị phần mềm kéo âm lượng (gain scaling).`;
  }

  if (data.effective >= data.declared - 1) {
    return `Xác nhận độ sâu bit thực tế đạt chuẩn ${data.declared}-bit (sử dụng trọn vẹn ${data.effective} mặt phẳng bit hoạt động).`;
  }

  return `Khai báo ${data.declared}-bit, thực tế sử dụng ${data.effective}-bit (lãng phí ${data.wasted_bits} mặt phẳng bit trống).`;
}

/**
 * Localize Pillar 2: Spectral Cutoff detail string
 */
export function localizeSpectralCutoffDetail(
  data: SpectralCutoffData,
  lang: Language
): string {
  if (lang === 'en') {
    return data.detail;
  }

  if (data.is_studio_filter && data.detected_cutoff_hz) {
    const fc = (data.detected_cutoff_hz / 1000).toFixed(2);
    const nyquist = (data.nyquist_hz / 1000).toFixed(2);
    const slope = data.rolloff_slope_db_per_khz ? Math.abs(data.rolloff_slope_db_per_khz).toFixed(1) : '—';
    if (data.detected_cutoff_hz >= 21000) {
      return `Tần số cắt tại ${fc} kHz (độ dốc ${slope} dB/kHz) sát ngưỡng Nyquist (${nyquist} kHz) là đặc tính chuẩn của Bộ lọc chống dội âm phòng thu (Studio Anti-Aliasing Filter). Toàn bộ dải phổ âm thanh 44.1 kHz nguyên bản đầy đủ, độ sâu bit 16-bit đạt chuẩn.`;
    }
    return `Phát hiện Bộ lọc dải cao kỹ thuật số phòng thu (Digital Master Filter) tại ${fc} kHz (độ dốc ${slope} dB/kHz). Đây là thiết lập chuẩn khi xuất bản nhạc số (Mora / Apple Music) nhằm tối ưu DAC và triệt tiêu nhiễu siêu cao. Toàn bộ phổ âm thanh 20 kHz nguyên bản đầy đủ, không có vết cắt nén lossy.`;
  }

  if (data.is_brickwall && data.detected_cutoff_hz) {
    const fc = (data.detected_cutoff_hz / 1000).toFixed(2);
    const slope = data.rolloff_slope_db_per_khz ? Math.abs(data.rolloff_slope_db_per_khz).toFixed(1) : '—';
    const enc = localizeEncoder(data.suspected_source_encoder, 'vi');
    return `Phát hiện vết cắt tần số dốc đứng (brickwall) tại ${fc} kHz (độ dốc suy hao ${slope} dB/kHz). Nguồn gốc nghi vấn: ${enc}.`;
  }

  const nyquist = (data.nyquist_hz / 1000).toFixed(1);
  return `Không phát hiện vết cắt brickwall nào lên tới giới hạn Nyquist (${nyquist} kHz). Dải tần âm thanh nguyên bản đầy đủ.`;
}

/**
 * Localize Pillar 3: Anti-Spoof detail string
 */
export function localizeAntiSpoofDetail(
  data: AntiSpoofData,
  lang: Language
): string {
  if (lang === 'en') {
    return data.detail;
  }

  if (data.fake_noise_injected) {
    const r = data.hf_envelope_correlation !== null ? data.hf_envelope_correlation.toFixed(3) : 'N/A';
    return `Phát hiện dải nhiễu trắng tĩnh nhân tạo ở tần số cao (hệ số tương quan r=${r}) — dấu hiệu bơm nhiễu nhằm đánh lừa bộ phân tích phổ.`;
  }

  if (data.holes_detected) {
    const pct = (data.spectral_holes_ratio * 100).toFixed(1);
    return `Phát hiện nhiều lỗ hổng năng lượng MDCT ở dải 12–16 kHz (chiếm ${pct}%) — dấu vết đặc trưng của thuật toán nén lossy (MP3/AAC).`;
  }

  const pct = (data.spectral_holes_ratio * 100).toFixed(1);
  if (data.detail && data.detail.includes('natural roll-off')) {
    return `Tỷ lệ lỗ nén MDCT dải 12–16 kHz: ${pct}% (sạch). | Không phát hiện năng lượng khả kiến trên 16.5 kHz — phổ tần cuộn dốc tự nhiên.`;
  }

  const r = data.hf_envelope_correlation !== null ? data.hf_envelope_correlation.toFixed(3) : 'N/A';
  return `Tỷ lệ lỗ nén MDCT dải 12–16 kHz: ${pct}% (sạch). | Hệ số tương quan dải cao r=${r} — phù hợp với dao động tự nhiên của âm thanh thực tế.`;
}

/**
 * Localize Pillar 4: Ultrasonic detail string
 */
export function localizeUltrasonicDetail(
  data: UltrasonicData,
  lang: Language
): string {
  if (lang === 'en') {
    return data.detail;
  }

  if (!data.applicable) {
    return 'Tần số lấy mẫu < 88.2 kHz — chỉ áp dụng cho định dạng Hi-Res / DSD để kiểm tra dải trên 24 kHz.';
  }

  if (data.fake_hires_upsampled) {
    return 'Container Hi-Res nhưng phổ tần bị cắt cụt đột ngột tại ranh giới 22.05 kHz của đĩa CD — tệp âm thanh CD 44.1 kHz bị nâng tần số lấy mẫu giả mạo.';
  }

  if (data.has_true_ultrasonic_transients) {
    return 'Xác nhận có sóng hài siêu âm thực thụ trải dài liên tục trên 24 kHz tới giới hạn Nyquist.';
  }

  return 'Không tìm thấy sóng hài siêu âm tương quan — nghi vấn nội dung nâng tần giả hoặc bản master tổng hợp.';
}

/**
 * Localize the top summary banner string
 */
export function localizeVerdictSummary(
  verdict: VerdictData,
  lang: Language
): string {
  if (lang === 'en') {
    return verdict.summary;
  }

  if (verdict.score >= 85 && (!verdict.summary || !verdict.summary.includes('Issues detected'))) {
    return 'Không phát hiện bất thường. Toàn bộ dải phổ tần âm thanh nguyên bản đầy đủ và độ sâu bit thực tế đạt chuẩn.';
  }

  // Strip notice if present
  let cleanSummary = verdict.summary.replace(/Notice: Unusual frequency characteristics detected.*$/i, '').trim();
  const raw = cleanSummary.replace(/^Issues detected:\s*/i, '').replace(/\.$/, '');
  const items = raw.split(';').map(s => s.trim()).filter(Boolean);

  const translatedItems = items.map(item => {
    // 1. Brickwall cutoff
    const bwMatch = item.match(/(?:Severe brickwall cutoff|Brickwall cutoff|Brickwall|High-frequency cutoff) at ([\d\.]+) kHz \(([^\)]+)\): likely (.+) \((-?\d+)\)/i);
    if (bwMatch) {
      const fc = bwMatch[1];
      const range = bwMatch[2].replace('<=', '≤');
      const source = bwMatch[3].includes('128k')
        ? 'nguồn nén MP3 128k / YouTube'
        : bwMatch[3].includes('192')
        ? 'nguồn nén MP3 192–256k hoặc AAC'
        : 'nguồn nén MP3 320k hoặc Opus';
      const pts = bwMatch[4];
      return `Vết cắt dốc đứng (brickwall) tại ${fc} kHz (${range}): đặc trưng ${source} (${pts} điểm)`;
    }

    // 2. Declared container holds lossy audio with cutoff
    const lossy24Match = item.match(/Declared (\d+)-bit container contains lossy audio with (?:brickwall )?cutoff(?: at ([\d\.]+) kHz)?.*? \((-?\d+)\)/i);
    if (lossy24Match) {
      const bits = lossy24Match[1];
      const fc = lossy24Match[2] ? ` tại ${lossy24Match[2]} kHz` : '';
      const pts = lossy24Match[3];
      return `Tệp khai báo container ${bits}-bit nhưng chứa âm thanh lossy bị cắt tần${fc} (${pts} điểm)`;
    }

    // 3. 16-bit padded
    const paddedMatch = item.match(/16-bit audio padded to (\d+)-bit container \((-?\d+)\)/i);
    if (paddedMatch) {
      return `Âm thanh 16-bit bị chèn số 0 giả mạo thành container ${paddedMatch[1]}-bit (${paddedMatch[2]} điểm)`;
    }

    // 4. Suspicious bit scaling
    const scalingMatch = item.match(/Suspicious bit scaling: bottom bits lack entropy.+?\((\d+)\)-bit.+?\((-?\d+)\)/i);
    if (scalingMatch) {
      return `Độ sâu bit đáng ngờ: các bit thấp thiếu độ biến thiên của master ${scalingMatch[1]}-bit thực tế (${scalingMatch[2]} điểm)`;
    }

    // 5. Stationary synthetic HF noise
    const noiseMatch = item.match(/Stationary synthetic HF noise (?:injected to spoof spectrum|detected) \((-?\d+)\)/i);
    if (noiseMatch) {
      return `Phát hiện dải nhiễu trắng tĩnh nhân tạo ở tần số cao (${noiseMatch[1]} điểm)`;
    }

    // 5b. Stealth noise layer (Module A)
    const stealthMatch = item.match(/Stealth (?:flat )?noise layer \/ missing HF transient coherence.*?(-?\d+)\)/i);
    if (stealthMatch) {
      return `Phát hiện dải nhiễu phẳng giả mạo / thiếu vệt xung đồng bộ ở dải cao >16 kHz (${stealthMatch[1]} điểm)`;
    }

    // 5c. Natural decay slope knee (Module B)
    const decayMatch = item.match(/(?:Slope knee discontinuity|Violates natural exponential decay: unnatural knee)(?: at ([\d\.]+) kHz)?.*?(-?\d+)\)/i);
    if (decayMatch) {
      const knee = decayMatch[1] ? ` tại ${decayMatch[1]} kHz` : '';
      return `Điểm gãy khúc phổ tần${knee} chuyển sang dải phẳng (${decayMatch[2]} điểm)`;
    }

    // 5d. AI artifacts (Module D)
    const aiMatch = item.match(/AI \/ Neural Vocoder artifacts detected.*?(-?\d+)\)/i);
    if (aiMatch) {
      return `Phát hiện tạo tác bù dải cao của AI / Neural Vocoder (${aiMatch[1]} điểm)`;
    }

    // 6. MDCT spectral holes
    const holesMatch = item.match(/MDCT spectral holes (?:in 12–16 kHz band )?\(ratio ([\d\.]+)\) \((-?\d+)\)/i);
    if (holesMatch) {
      const pct = (parseFloat(holesMatch[1]) * 100).toFixed(1);
      return `Phát hiện lỗ hổng lượng tử hóa MDCT dải 12–16 kHz (tỷ lệ ${pct}%) (${holesMatch[2]} điểm)`;
    }

    // 7. Hi-Res upsampling
    const hiresMatch = item.match(/Brickwall (?:cutoff )?at CD boundary.*?in Hi-Res container \((-?\d+)\)/i);
    if (hiresMatch) {
      return `Bị cắt cụt ở ranh giới CD 22.05 kHz trong container Hi-Res (nâng tần giả) (${hiresMatch[1]} điểm)`;
    }

    // 8. Natural rolloff
    const rolloffMatch = item.match(/Gradual (?:natural|acoustic) roll-off below 18 kHz \((-?\d+)\)/i);
    if (rolloffMatch) {
      return `Dải tần cuộn dốc tự nhiên dưới 18 kHz (${rolloffMatch[1]} điểm)`;
    }

    return item;
  });

  return `Phát hiện bất thường: ${translatedItems.join('; ')}.`;
}

/**
 * Localize Module A: Phase & Transient Coherence detail
 */
export function localizePhaseCoherenceDetail(
  data: { hf_time_variance_db: number; transient_concurrence_ratio: number; is_stealth_noise_layer: boolean; status: string; detail: string },
  lang: Language
): string {
  if (lang === 'en') {
    if (data.status === 'NO_HF_ENERGY') {
      return 'No detectable energy above 16 kHz — high frequencies completely suppressed by brickwall cutoff.';
    }
    if (data.is_stealth_noise_layer) {
      return `WARNING: High frequencies (>16 kHz) have energy but are flat as a lake (variance σ=${data.hf_time_variance_db.toFixed(2)} dB, transient sync ${(data.transient_concurrence_ratio * 100).toFixed(1)}%). Missing natural acoustic transient spikes — consistent with injected noise or dither padding.`;
    }
    return `Good phase and transient coherence (variance σ=${data.hf_time_variance_db.toFixed(2)} dB, transient sync ${(data.transient_concurrence_ratio * 100).toFixed(1)}%). Verified natural instrument attacks synchronized across mid and high bands.`;
  }
  return data.detail;
}

/**
 * Localize Module B: Natural Decay detail
 */
export function localizeNaturalDecayDetail(
  data: { knee_frequency_khz: number | null; slope_pre_knee_db_per_khz: number | null; slope_post_knee_db_per_khz: number | null; decay_discontinuity_score: number; violates_natural_decay: boolean; status: string; detail: string },
  lang: Language
): string {
  if (lang === 'en') {
    if (data.violates_natural_decay && data.knee_frequency_khz) {
      return `WARNING: Violates physical acoustic decay! Abrupt knee fracture detected at ${data.knee_frequency_khz.toFixed(2)} kHz: rolling off at ${data.slope_pre_knee_db_per_khz?.toFixed(1)} dB/kHz then suddenly flattening into an unnatural shelf at ${data.slope_post_knee_db_per_khz?.toFixed(1)} dB/kHz. Characteristic mark of a lossy lowpass filter.`;
    }
    if (data.knee_frequency_khz) {
      return `Spectral knee detected at ${data.knee_frequency_khz.toFixed(2)} kHz, but high-frequency energy remains strong and extends to >21 kHz studio filter. Verified as authentic musical mix/mastering characteristic, not lossy compression.`;
    }
    return `Spectral decay follows natural acoustic exponential law (slope ${data.slope_pre_knee_db_per_khz?.toFixed(2)} dB/kHz, no abnormal knee or flat shelf).`;
  }
  return data.detail;
}

/**
 * Localize Module C: AccurateRip detail
 */
export function localizeAccurateRipDetail(
  data: { crc32_v1: string; crc32_v2: string; track_crc: string; db_status: string; confidence: number; detail: string },
  lang: Language
): string {
  if (lang === 'en') {
    if (data.db_status === 'CONFIRMED_BIT_PERFECT') {
      return `100% BIT-PERFECT VERIFIED: Checksum ${data.track_crc} matches original CD pressings in AccurateRip/CTDB database (confidence count: ${data.confidence}). Absolute genuine Redbook CD rip.`;
    }
    if (data.db_status === 'NON_REDBOOK') {
      return `Audio format is Hi-Res / non-Redbook (${data.track_crc}). AccurateRip database verification strictly applies to 16-bit 44.1 kHz Redbook CD pressings.`;
    }
    return `Checksums: v1=${data.crc32_v1}, v2=${data.crc32_v2}, Track=${data.track_crc}. Not currently catalogued in AccurateRip database (typical for independent releases or digital web masters).`;
  }
  return data.detail;
}

/**
 * Localize Module D: AI Artifacts detail
 */
export function localizeAiArtifactsDetail(
  data: { phase_jitter_entropy: number; spectral_repetition_score: number; comb_ripple_db: number; ai_artifacts_detected: boolean; status: string; detail: string },
  lang: Language
): string {
  if (lang === 'en') {
    if (data.ai_artifacts_detected) {
      return `WARNING: AI / Neural Vocoder bandwidth extension artifacts detected! High phase jitter (${data.phase_jitter_entropy.toFixed(3)}) combined with spectral pattern repetition (${data.spectral_repetition_score.toFixed(2)}) and comb filtering (${data.comb_ripple_db.toFixed(1)} dB). Consistent with AI models hallucinating high frequencies.`;
    }
    return `No AI or neural vocoder artifacts detected (phase stability ${(1 - data.phase_jitter_entropy).toFixed(2)}, normal spectral repetition ${data.spectral_repetition_score.toFixed(2)}).`;
  }
  return data.detail;
}

