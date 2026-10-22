// components/AdvancedGrid.tsx — Advanced 4-Pillar Verification Engine UI
import React, { useState } from 'react';
import {
  Activity,
  TrendingDown,
  Disc,
  Cpu,
  CheckCircle2,
  XCircle,
  Info,
  HelpCircle,
} from 'lucide-react';
import type { AdvancedModulesData } from '../api';
import { translations, type Language } from '../i18n';
import { ExplainModal, type ExplanationKey } from './ExplainModal';
import {
  localizePhaseCoherenceDetail,
  localizeNaturalDecayDetail,
  localizeAccurateRipDetail,
  localizeAiArtifactsDetail,
} from '../utils/localize';

interface Props {
  advanced: AdvancedModulesData;
  t: typeof translations['en']['advanced'];
  lang: Language;
}

function StatusBadge({
  status,
  labels,
}: {
  status: 'passed' | 'failed' | 'info' | 'confirmed';
  labels: { text: string };
}) {
  if (status === 'confirmed') {
    return (
      <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-500/20 border border-emerald-400 text-emerald-300 text-[11px] font-black tracking-wide shadow-[0_0_12px_rgba(16,185,129,0.4)] animate-pulse">
        <CheckCircle2 size={14} className="stroke-[3]" />
        <span>{labels.text}</span>
      </div>
    );
  }
  if (status === 'passed') {
    return (
      <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-500/15 border border-emerald-500/40 text-emerald-400 text-[11px] font-bold shadow-sm shadow-emerald-950/40">
        <CheckCircle2 size={14} className="stroke-[2.5]" />
        <span>{labels.text}</span>
      </div>
    );
  }
  if (status === 'info') {
    return (
      <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-slate-800/80 border border-slate-700 text-slate-300 text-[11px] font-medium">
        <Info size={13} className="text-sky-400" />
        <span>{labels.text}</span>
      </div>
    );
  }
  // High-visibility, glowing Red X for failure
  return (
    <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-rose-500/25 border-2 border-rose-500 text-rose-300 text-[11px] font-black tracking-wider shadow-[0_0_16px_rgba(244,63,94,0.6)] animate-pulse">
      <XCircle size={15} className="text-rose-400 stroke-[3]" />
      <span>{labels.text}</span>
    </div>
  );
}

function Metric({ label, value, sub }: { label: string; value: React.ReactNode; sub?: string }) {
  return (
    <div className="flex flex-col gap-0.5">
      <span className="text-[10px] uppercase tracking-wider font-semibold text-slate-400">{label}</span>
      <span className="text-xs sm:text-sm font-semibold mono text-slate-100">{value}</span>
      {sub && <span className="text-[10px] text-slate-500">{sub}</span>}
    </div>
  );
}

export function AdvancedGrid({ advanced, t, lang }: Props) {
  const [explainKey, setExplainKey] = useState<ExplanationKey | null>(null);
  const { phase_coherence, natural_decay, accuraterip, ai_artifacts } = advanced;

  // Module A status
  const modAOk = !phase_coherence.is_stealth_noise_layer && phase_coherence.status !== 'FAILED';
  const modANoEnergy = phase_coherence.status === 'NO_HF_ENERGY';

  // Module B status
  const modBOk = !natural_decay.violates_natural_decay;

  // Module C status
  const modCConfirmed = accuraterip.db_status === 'CONFIRMED_BIT_PERFECT';
  const modCNonRedbook = accuraterip.db_status === 'NON_REDBOOK';

  // Module D status
  const modDOk = !ai_artifacts.ai_artifacts_detected;

  return (
    <div className="space-y-4">
      {/* Section Header */}
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-2 border-b border-slate-800/80 pb-3">
        <div>
          <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 text-[11px] font-medium mb-1.5">
            <Activity size={12} />
            <span>{t.sectionBadge}</span>
          </div>
          <h2 className="text-lg sm:text-xl font-bold tracking-tight text-white flex items-center gap-2">
            {t.sectionTitle}
          </h2>
          <p className="text-xs sm:text-sm text-slate-400">
            {t.sectionSubtitle}
          </p>
        </div>
      </div>

      {/* 4 Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* ── Card A: Phase & Transient Coherence ── */}
        <div
          className={`relative rounded-xl border p-4 sm:p-5 flex flex-col justify-between transition-all duration-200 ${
            !modAOk
              ? 'bg-rose-950/20 border-rose-500/70 shadow-[0_0_24px_rgba(244,63,94,0.18)]'
              : 'bg-slate-900/60 border-slate-800/80 hover:border-slate-700/80'
          }`}
        >
          <div>
            <div className="flex items-start justify-between gap-3 mb-3">
              <div className="flex items-center gap-2.5">
                <div
                  className={`w-9 h-9 rounded-lg flex items-center justify-center border ${
                    !modAOk
                      ? 'bg-rose-500/20 border-rose-500/50 text-rose-400'
                      : 'bg-indigo-500/10 border-indigo-500/30 text-indigo-400'
                  }`}
                >
                  <Activity size={18} />
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-slate-100">{t.moduleA.title}</h3>
                  <p className="text-[11px] text-slate-400">{t.moduleA.subtitle}</p>
                </div>
              </div>
              <div className="flex items-center gap-1.5 shrink-0">
                <button
                  onClick={() => setExplainKey('phaseCoherence')}
                  className="flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded-full bg-cyan-500/10 hover:bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 transition-all cursor-pointer shadow-sm hover:scale-105 active:scale-95"
                  title={translations[lang].explanationsBtn}
                >
                  <HelpCircle size={11} className="shrink-0 text-cyan-400" />
                  <span>{translations[lang].explanationsBtn}</span>
                </button>
                <StatusBadge
                  status={modANoEnergy ? 'info' : modAOk ? 'passed' : 'failed'}
                  labels={{
                    text: modANoEnergy
                      ? t.moduleA.statusNoEnergy
                      : modAOk
                      ? t.moduleA.statusPassed
                      : t.moduleA.statusFailed,
                  }}
                />
              </div>
            </div>

            <div className="grid grid-cols-3 gap-3 p-3 rounded-lg bg-slate-950/40 border border-slate-800/50 mb-3">
              <Metric
                label={t.moduleA.variance}
                value={`${phase_coherence.hf_time_variance_db.toFixed(2)} dB`}
                sub={phase_coherence.hf_time_variance_db >= 2.5 ? 'Độ động cao' : 'Phẳng / Tĩnh'}
              />
              <Metric
                label={t.moduleA.concurrence}
                value={`${(phase_coherence.transient_concurrence_ratio * 100).toFixed(1)}%`}
                sub={phase_coherence.transient_concurrence_ratio >= 0.3 ? 'Khớp vệt xung' : 'Mất đồng bộ'}
              />
              <Metric
                label={t.moduleA.stealthNoise}
                value={
                  phase_coherence.is_stealth_noise_layer ? (
                    <span className="text-rose-400 font-bold">CÓ (GIẢ MẠO)</span>
                  ) : (
                    <span className="text-emerald-400">Không</span>
                  )
                }
              />
            </div>
          </div>

          <div
            className={`text-[11px] leading-relaxed p-2.5 rounded-md border ${
              !modAOk
                ? 'bg-rose-950/40 border-rose-500/30 text-rose-200'
                : 'bg-slate-950/30 border-slate-800/30 text-slate-400'
            }`}
          >
            {localizePhaseCoherenceDetail(phase_coherence, lang)}
          </div>
        </div>

        {/* ── Card B: Natural Decay Rate & Knee Discontinuity ── */}
        <div
          className={`relative rounded-xl border p-4 sm:p-5 flex flex-col justify-between transition-all duration-200 ${
            !modBOk
              ? 'bg-rose-950/20 border-rose-500/70 shadow-[0_0_24px_rgba(244,63,94,0.18)]'
              : 'bg-slate-900/60 border-slate-800/80 hover:border-slate-700/80'
          }`}
        >
          <div>
            <div className="flex items-start justify-between gap-3 mb-3">
              <div className="flex items-center gap-2.5">
                <div
                  className={`w-9 h-9 rounded-lg flex items-center justify-center border ${
                    !modBOk
                      ? 'bg-rose-500/20 border-rose-500/50 text-rose-400'
                      : 'bg-amber-500/10 border-amber-500/30 text-amber-400'
                  }`}
                >
                  <TrendingDown size={18} />
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-slate-100">{t.moduleB.title}</h3>
                  <p className="text-[11px] text-slate-400">{t.moduleB.subtitle}</p>
                </div>
              </div>
              <div className="flex items-center gap-1.5 shrink-0">
                <button
                  onClick={() => setExplainKey('naturalDecay')}
                  className="flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded-full bg-cyan-500/10 hover:bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 transition-all cursor-pointer shadow-sm hover:scale-105 active:scale-95"
                  title={translations[lang].explanationsBtn}
                >
                  <HelpCircle size={11} className="shrink-0 text-cyan-400" />
                  <span>{translations[lang].explanationsBtn}</span>
                </button>
                <StatusBadge
                  status={modBOk ? 'passed' : 'failed'}
                  labels={{
                    text: modBOk ? t.moduleB.statusPassed : t.moduleB.statusFailed,
                  }}
                />
              </div>
            </div>

            <div className="grid grid-cols-3 gap-3 p-3 rounded-lg bg-slate-950/40 border border-slate-800/50 mb-3">
              <Metric
                label={t.moduleB.kneeFreq}
                value={
                  natural_decay.knee_frequency_khz
                    ? `${natural_decay.knee_frequency_khz.toFixed(2)} kHz`
                    : (lang === 'vi' ? 'Không phát hiện' : 'None detected')
                }
                sub={
                  natural_decay.knee_frequency_khz
                    ? (natural_decay.violates_natural_decay
                        ? (lang === 'vi' ? 'Vách gãy bộ lọc' : 'Filter Knee')
                        : (lang === 'vi' ? 'Bản phối âm nhạc' : 'Mix Characteristic'))
                    : (lang === 'vi' ? 'Mượt mà' : 'Smooth')
                }
              />
              <Metric
                label={t.moduleB.slopePre}
                value={
                  natural_decay.slope_pre_knee_db_per_khz !== null
                    ? `${natural_decay.slope_pre_knee_db_per_khz.toFixed(1)} dB/kHz`
                    : '—'
                }
              />
              <Metric
                label={t.moduleB.slopePost}
                value={
                  natural_decay.slope_post_knee_db_per_khz !== null
                    ? `${natural_decay.slope_post_knee_db_per_khz.toFixed(1)} dB/kHz`
                    : '—'
                }
                sub={
                  natural_decay.slope_post_knee_db_per_khz !== null &&
                  Math.abs(natural_decay.slope_post_knee_db_per_khz) < 2.0
                    ? (natural_decay.violates_natural_decay
                        ? (lang === 'vi' ? 'Dải phẳng nhân tạo' : 'Artificial flat shelf')
                        : (lang === 'vi' ? 'Dải cao tự nhiên' : 'Natural HF plateau'))
                    : undefined
                }
              />
            </div>
          </div>

          <div
            className={`text-[11px] leading-relaxed p-2.5 rounded-md border ${
              !modBOk
                ? 'bg-rose-950/40 border-rose-500/30 text-rose-200'
                : 'bg-slate-950/30 border-slate-800/30 text-slate-400'
            }`}
          >
            {localizeNaturalDecayDetail(natural_decay, lang)}
          </div>
        </div>

        {/* ── Card C: AccurateRip / CTDB CRC Check ── */}
        <div className="relative rounded-xl border border-slate-800/80 bg-slate-900/60 p-4 sm:p-5 flex flex-col justify-between hover:border-slate-700/80 transition-all duration-200">
          <div>
            <div className="flex items-start justify-between gap-3 mb-3">
              <div className="flex items-center gap-2.5">
                <div
                  className={`w-9 h-9 rounded-lg flex items-center justify-center border ${
                    modCConfirmed
                      ? 'bg-emerald-500/20 border-emerald-500/50 text-emerald-400'
                      : 'bg-cyan-500/10 border-cyan-500/30 text-cyan-400'
                  }`}
                >
                  <Disc size={18} />
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-slate-100">{t.moduleC.title}</h3>
                  <p className="text-[11px] text-slate-400">{t.moduleC.subtitle}</p>
                </div>
              </div>
              <div className="flex items-center gap-1.5 shrink-0">
                <button
                  onClick={() => setExplainKey('accurateRip')}
                  className="flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded-full bg-cyan-500/10 hover:bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 transition-all cursor-pointer shadow-sm hover:scale-105 active:scale-95"
                  title={translations[lang].explanationsBtn}
                >
                  <HelpCircle size={11} className="shrink-0 text-cyan-400" />
                  <span>{translations[lang].explanationsBtn}</span>
                </button>
                <StatusBadge
                  status={modCConfirmed ? 'confirmed' : 'info'}
                  labels={{
                    text: modCConfirmed
                      ? t.moduleC.statusConfirmed
                      : modCNonRedbook
                      ? t.moduleC.statusNonRedbook
                      : t.moduleC.statusNotInDb,
                  }}
                />
              </div>
            </div>

            <div className="grid grid-cols-3 gap-3 p-3 rounded-lg bg-slate-950/40 border border-slate-800/50 mb-3">
              <Metric label={t.moduleC.trackCrc} value={accuraterip.track_crc} />
              <Metric label={t.moduleC.crcV1} value={accuraterip.crc32_v1} />
              <Metric
                label={t.moduleC.dbStatus}
                value={
                  modCConfirmed ? (
                    <span className="text-emerald-400 font-bold">100% CD MATCH</span>
                  ) : modCNonRedbook ? (
                    'Hi-Res / Digital'
                  ) : (
                    'Chưa lưu trữ'
                  )
                }
              />
            </div>
          </div>

          <div className="text-[11px] leading-relaxed p-2.5 rounded-md border bg-slate-950/30 border-slate-800/30 text-slate-400">
            {localizeAccurateRipDetail(accuraterip, lang)}
          </div>
        </div>

        {/* ── Card D: AI & Neural Vocoder Artifacts ── */}
        <div
          className={`relative rounded-xl border p-4 sm:p-5 flex flex-col justify-between transition-all duration-200 ${
            !modDOk
              ? 'bg-rose-950/20 border-rose-500/70 shadow-[0_0_24px_rgba(244,63,94,0.18)]'
              : 'bg-slate-900/60 border-slate-800/80 hover:border-slate-700/80'
          }`}
        >
          <div>
            <div className="flex items-start justify-between gap-3 mb-3">
              <div className="flex items-center gap-2.5">
                <div
                  className={`w-9 h-9 rounded-lg flex items-center justify-center border ${
                    !modDOk
                      ? 'bg-rose-500/20 border-rose-500/50 text-rose-400'
                      : 'bg-violet-500/10 border-violet-500/30 text-violet-400'
                  }`}
                >
                  <Cpu size={18} />
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-slate-100">{t.moduleD.title}</h3>
                  <p className="text-[11px] text-slate-400">{t.moduleD.subtitle}</p>
                </div>
              </div>
              <div className="flex items-center gap-1.5 shrink-0">
                <button
                  onClick={() => setExplainKey('aiArtifacts')}
                  className="flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded-full bg-cyan-500/10 hover:bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 transition-all cursor-pointer shadow-sm hover:scale-105 active:scale-95"
                  title={translations[lang].explanationsBtn}
                >
                  <HelpCircle size={11} className="shrink-0 text-cyan-400" />
                  <span>{translations[lang].explanationsBtn}</span>
                </button>
                <StatusBadge
                  status={modDOk ? 'passed' : 'failed'}
                  labels={{
                    text: modDOk ? t.moduleD.statusPassed : t.moduleD.statusFailed,
                  }}
                />
              </div>
            </div>

            <div className="grid grid-cols-3 gap-3 p-3 rounded-lg bg-slate-950/40 border border-slate-800/50 mb-3">
              <Metric
                label={t.moduleD.phaseJitter}
                value={ai_artifacts.phase_jitter_entropy.toFixed(3)}
                sub={ai_artifacts.phase_jitter_entropy > 0.85 ? 'Pha hỗn loạn' : 'Pha liên tục'}
              />
              <Metric
                label={t.moduleD.repetition}
                value={ai_artifacts.spectral_repetition_score.toFixed(2)}
                sub={ai_artifacts.spectral_repetition_score > 0.65 ? 'Lặp cấu trúc mẫu' : 'Tự nhiên'}
              />
              <Metric
                label={t.moduleD.combRipple}
                value={`${ai_artifacts.comb_ripple_db.toFixed(1)} dB`}
                sub={ai_artifacts.comb_ripple_db > 8.0 ? 'Gợn sóng Comb' : 'Bình thường'}
              />
            </div>
          </div>

          <div
            className={`text-[11px] leading-relaxed p-2.5 rounded-md border ${
              !modDOk
                ? 'bg-rose-950/40 border-rose-500/30 text-rose-200'
                : 'bg-slate-950/30 border-slate-800/30 text-slate-400'
            }`}
          >
            {localizeAiArtifactsDetail(ai_artifacts, lang)}
          </div>
        </div>
      </div>

      <ExplainModal
        metricKey={explainKey}
        onClose={() => setExplainKey(null)}
        t={translations[lang]}
        lang={lang}
      />
    </div>
  );
}
