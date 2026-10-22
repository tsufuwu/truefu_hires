import { useState } from 'react';
import { Binary, Scissors, ShieldAlert, Zap, CheckCircle2, XCircle, AlertTriangle, MinusCircle, Sliders, ShieldCheck, HelpCircle } from 'lucide-react';
import type { BitDepthData, SpectralCutoffData, AntiSpoofData, UltrasonicData } from '../api';
import { translations, type Language } from '../i18n';
import { ExplainModal, type ExplanationKey } from './ExplainModal';
import {
  localizeBitDepthDetail,
  localizeSpectralCutoffDetail,
  localizeAntiSpoofDetail,
  localizeUltrasonicDetail,
  localizeEncoder,
} from '../utils/localize';

interface Props {
  bitDepth: BitDepthData;
  spectral: SpectralCutoffData;
  antiSpoof: AntiSpoofData;
  ultrasonic: UltrasonicData;
  t: typeof translations['en']['pillars'];
  lang?: Language;
}

function StatusBadge({
  ok,
  na,
  badges,
}: {
  ok: boolean | null;
  na?: boolean;
  badges: typeof translations['en']['pillars']['statusBadges'];
}) {
  if (na) {
    return (
      <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-slate-800/80 border border-slate-700 text-slate-400 text-xs font-semibold">
        <MinusCircle size={14} />
        <span>{badges.na}</span>
      </div>
    );
  }
  if (ok) {
    return (
      <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-500/15 border border-emerald-500/40 text-emerald-400 text-xs font-bold shadow-sm shadow-emerald-950/40">
        <CheckCircle2 size={15} className="stroke-[2.5]" />
        <span>{badges.passed}</span>
      </div>
    );
  }
  // High-visibility, prominent Red X badge for failed cards
  return (
    <div className="flex items-center gap-1.5 px-3.5 py-1 rounded-full bg-rose-500/25 border-2 border-rose-500 text-rose-300 text-xs font-black tracking-wider shadow-[0_0_15px_rgba(244,63,94,0.55)] animate-pulse">
      <XCircle size={16} className="text-rose-400 stroke-[3]" />
      <span>{badges.failed}</span>
    </div>
  );
}

function Metric({ label, value, sub }: { label: string; value: React.ReactNode; sub?: string }) {
  return (
    <div className="flex flex-col gap-0.5">
      <span className="text-[11px] sm:text-xs uppercase tracking-wider font-semibold text-slate-400">{label}</span>
      <span className="text-sm sm:text-base font-bold mono text-slate-100">{value}</span>
      {sub && <span className="text-[10px] text-slate-500">{sub}</span>}
    </div>
  );
}

// ── Pillar 1: Bit Depth ───────────────────────────────────────────────────────
function BitDepthCard({
  data,
  spectral,
  t,
  lang,
  onExplain,
}: {
  data: BitDepthData;
  spectral: SpectralCutoffData;
  t: typeof translations['en']['pillars'];
  lang: Language;
  onExplain: (key: ExplanationKey) => void;
}) {
  const isOk = !data.is_padded && !data.suspicious_scaling;

  const declared = data.declared;
  const effective = data.effective;
  const totalSlots = declared;
  const activeSlots = effective;
  const deadSlots = totalSlots - activeSlots;

  const localizedDetail = localizeBitDepthDetail(data, spectral, lang);

  return (
    <div
      className={`card p-5 fade-in flex flex-col gap-4 transition-all duration-300 ${
        isOk
          ? 'border-slate-800/80 hover:border-slate-700/80'
          : 'border-2 border-rose-500/70 bg-gradient-to-b from-rose-950/35 via-slate-900/90 to-slate-900 shadow-[0_0_25px_rgba(244,63,94,0.2)] ring-1 ring-rose-500/30'
      }`}
      id="pillar-bit-depth"
    >
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <div className="flex items-center gap-2">
          <div
            className="w-8 h-8 rounded-lg flex items-center justify-center"
            style={{
              background: isOk ? 'rgba(59, 130, 246, 0.15)' : 'rgba(244, 63, 94, 0.2)',
              border: isOk ? '1px solid rgba(59, 130, 246, 0.3)' : '1px solid rgba(244, 63, 94, 0.5)',
            }}
          >
            <Binary size={16} style={{ color: isOk ? 'var(--accent-blue)' : 'var(--accent-red)' }} />
          </div>
          <span className="font-bold text-sm sm:text-base text-slate-100">{t.bitDepth.title}</span>
        </div>
        <div className="flex items-center gap-1.5">
          <button
            onClick={() => onExplain('bitDepth')}
            className="flex items-center gap-1 text-[11px] font-semibold px-2.5 py-1 rounded-full bg-cyan-500/10 hover:bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 transition-all cursor-pointer shadow-sm hover:scale-105 active:scale-95"
            title={translations[lang].explanationsBtn}
          >
            <HelpCircle size={12} className="shrink-0 text-cyan-400" />
            <span>{translations[lang].explanationsBtn}</span>
          </button>
          <StatusBadge ok={isOk} badges={t.statusBadges} />
        </div>
      </div>

      {/* Bit slot visualiser */}
      <div className="flex items-center gap-0 flex-wrap">
        {Array.from({ length: totalSlots }).map((_, i) => {
          const isActive = i < activeSlots;
          return (
            <span
              key={i}
              className={`bit-slot ${isActive ? 'bit-slot-active' : 'bit-slot-dead'}`}
              title={isActive ? `Bit ${declared - i}` : 'Dead (zero-padded)'}
            />
          );
        })}
      </div>
      <p className="text-xs text-slate-400">
        <strong className="text-cyan-400">{activeSlots}</strong> {t.bitDepth.activePlanes} /{' '}
        <strong className={deadSlots > 0 ? 'text-rose-400' : 'text-slate-500'}>{deadSlots}</strong> {t.bitDepth.deadPlanes}
      </p>

      <div className="grid grid-cols-2 gap-3 pt-1 border-t border-slate-800/60">
        <Metric label={t.bitDepth.declared} value={`${data.declared}-bit`} />
        <Metric label={t.bitDepth.effective} value={`${data.effective}-bit`} />
        <Metric label={t.bitDepth.wasted} value={`${data.wasted_bits} bits`} />
        <Metric label={t.bitDepth.padded} value={data.is_padded ? t.bitDepth.yes : t.bitDepth.no} />
      </div>

      <div
        className={`text-xs sm:text-[13px] leading-relaxed p-3.5 rounded-xl border ${
          isOk
            ? 'border-slate-800/80 bg-slate-900/60 text-slate-300'
            : 'border-2 border-rose-500/40 bg-rose-950/50 text-rose-200 font-medium shadow-inner'
        }`}
      >
        {!isOk && (
          <span className="flex items-center gap-1.5 text-rose-400 font-bold uppercase text-[11px] tracking-wider mb-1">
            <AlertTriangle size={14} className="stroke-[2.5]" />
            {t.statusBadges.anomalyAlert}
          </span>
        )}
        <p>{localizedDetail}</p>
      </div>
    </div>
  );
}

// ── Pillar 2: Spectral Cutoff ─────────────────────────────────────────────────
function SpectralCutoffCard({
  data,
  t,
  lang,
  onExplain,
}: {
  data: SpectralCutoffData;
  t: typeof translations['en']['pillars'];
  lang: Language;
  onExplain: (key: ExplanationKey) => void;
}) {
  const isStudioFilter = !!data.is_studio_filter;
  const isOk = !data.is_brickwall || isStudioFilter;
  const localizedDetail = localizeSpectralCutoffDetail(data, lang);
  const localizedEnc = localizeEncoder(data.suspected_source_encoder, lang);

  return (
    <div
      className={`card p-5 fade-in flex flex-col gap-4 transition-all duration-300 ${
        isOk
          ? 'border-slate-800/80 hover:border-slate-700/80'
          : 'border-2 border-rose-500/70 bg-gradient-to-b from-rose-950/35 via-slate-900/90 to-slate-900 shadow-[0_0_25px_rgba(244,63,94,0.2)] ring-1 ring-rose-500/30'
      }`}
      id="pillar-spectral-cutoff"
    >
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <div className="flex items-center gap-2">
          <div
            className="w-8 h-8 rounded-lg flex items-center justify-center"
            style={{
              background: isStudioFilter
                ? 'rgba(16, 185, 129, 0.15)'
                : isOk
                ? 'rgba(244, 63, 94, 0.12)'
                : 'rgba(244, 63, 94, 0.25)',
              border: isStudioFilter
                ? '1px solid rgba(16, 185, 129, 0.4)'
                : isOk
                ? '1px solid rgba(244, 63, 94, 0.3)'
                : '1px solid rgba(244, 63, 94, 0.6)',
            }}
          >
            {isStudioFilter ? (
              <Sliders size={16} className="text-emerald-400" />
            ) : (
              <Scissors size={16} style={{ color: 'var(--accent-red)' }} />
            )}
          </div>
          <span className="font-bold text-sm sm:text-base text-slate-100">{t.spectralCutoff.title}</span>
        </div>
        <div className="flex items-center gap-1.5">
          <button
            onClick={() => onExplain('spectralCutoff')}
            className="flex items-center gap-1 text-[11px] font-semibold px-2.5 py-1 rounded-full bg-cyan-500/10 hover:bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 transition-all cursor-pointer shadow-sm hover:scale-105 active:scale-95"
            title={translations[lang].explanationsBtn}
          >
            <HelpCircle size={12} className="shrink-0 text-cyan-400" />
            <span>{translations[lang].explanationsBtn}</span>
          </button>
          <StatusBadge ok={isOk} badges={t.statusBadges} />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <Metric label={t.spectralCutoff.nyquist} value={`${(data.nyquist_hz / 1000).toFixed(2)} kHz`} />
        <Metric
          label={t.spectralCutoff.cutoff}
          value={data.detected_cutoff_hz != null ? `${(data.detected_cutoff_hz / 1000).toFixed(2)} kHz` : t.spectralCutoff.none}
        />
        <Metric
          label={t.spectralCutoff.slope}
          value={data.rolloff_slope_db_per_khz != null ? `${data.rolloff_slope_db_per_khz.toFixed(1)} dB/kHz` : '—'}
        />
        <Metric
          label={t.spectralCutoff.brickwall}
          value={isStudioFilter ? t.spectralCutoff.studioFilter : (data.is_brickwall ? t.spectralCutoff.yes : t.spectralCutoff.no)}
        />
      </div>

      {data.suspected_source_encoder && (
        <div
          className="flex items-center gap-2 px-3 py-2 rounded-xl"
          style={{
            background: isStudioFilter ? 'rgba(16, 185, 129, 0.12)' : 'rgba(244, 63, 94, 0.15)',
            border: isStudioFilter ? '1px solid rgba(16, 185, 129, 0.35)' : '1px solid rgba(244, 63, 94, 0.35)',
          }}
        >
          {isStudioFilter ? (
            <ShieldCheck size={14} className="text-emerald-400 shrink-0" />
          ) : (
            <AlertTriangle size={14} className="text-rose-400 shrink-0" />
          )}
          <span
            className={`text-[11px] font-bold truncate ${
              isStudioFilter ? 'text-emerald-300' : 'text-rose-300'
            }`}
          >
            {localizedEnc}
          </span>
        </div>
      )}

      <div
        className={`text-[11px] leading-relaxed p-3 rounded-xl border ${
          isStudioFilter
            ? 'border-emerald-500/30 bg-emerald-950/20 text-emerald-200'
            : isOk
            ? 'border-slate-800/80 bg-slate-900/60 text-slate-300'
            : 'border-2 border-rose-500/40 bg-rose-950/50 text-rose-200 font-medium shadow-inner'
        }`}
      >
        {isStudioFilter ? (
          <span className="flex items-center gap-1.5 text-emerald-400 font-bold uppercase text-[10px] tracking-wider mb-1">
            <ShieldCheck size={13} className="stroke-[2.5]" />
            {t.statusBadges.studioVerified}
          </span>
        ) : !isOk ? (
          <span className="flex items-center gap-1.5 text-rose-400 font-bold uppercase text-[10px] tracking-wider mb-1">
            <AlertTriangle size={13} className="stroke-[2.5]" />
            {t.statusBadges.anomalyAlert}
          </span>
        ) : null}
        <p>{localizedDetail}</p>
      </div>
    </div>
  );
}

// ── Pillar 3: Anti-Spoof ──────────────────────────────────────────────────────
function AntiSpoofCard({
  data,
  t,
  lang,
  onExplain,
}: {
  data: AntiSpoofData;
  t: typeof translations['en']['pillars'];
  lang: Language;
  onExplain: (key: ExplanationKey) => void;
}) {
  const isOk = !data.holes_detected && !data.fake_noise_injected;
  const localizedDetail = localizeAntiSpoofDetail(data, lang);

  return (
    <div
      className={`card p-5 fade-in flex flex-col gap-4 transition-all duration-300 ${
        isOk
          ? 'border-slate-800/80 hover:border-slate-700/80'
          : 'border-2 border-rose-500/70 bg-gradient-to-b from-rose-950/35 via-slate-900/90 to-slate-900 shadow-[0_0_25px_rgba(244,63,94,0.2)] ring-1 ring-rose-500/30'
      }`}
      id="pillar-anti-spoof"
    >
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <div className="flex items-center gap-2">
          <div
            className="w-8 h-8 rounded-lg flex items-center justify-center"
            style={{ background: 'rgba(245, 158, 11, 0.15)', border: '1px solid rgba(245, 158, 11, 0.3)' }}
          >
            <ShieldAlert size={16} style={{ color: 'var(--accent-amber)' }} />
          </div>
          <span className="font-bold text-sm sm:text-base text-slate-100">{t.antiSpoof.title}</span>
        </div>
        <div className="flex items-center gap-1.5">
          <button
            onClick={() => onExplain('antiSpoof')}
            className="flex items-center gap-1 text-[11px] font-semibold px-2.5 py-1 rounded-full bg-cyan-500/10 hover:bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 transition-all cursor-pointer shadow-sm hover:scale-105 active:scale-95"
            title={translations[lang].explanationsBtn}
          >
            <HelpCircle size={12} className="shrink-0 text-cyan-400" />
            <span>{translations[lang].explanationsBtn}</span>
          </button>
          <StatusBadge ok={isOk} badges={t.statusBadges} />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <Metric label={t.antiSpoof.holesRatio} value={data.spectral_holes_ratio.toFixed(4)} sub="12–16 kHz" />
        <Metric label={t.antiSpoof.holesDetected} value={data.holes_detected ? t.antiSpoof.yes : t.antiSpoof.no} />
        <Metric
          label={t.antiSpoof.correlation}
          value={data.hf_envelope_correlation != null ? data.hf_envelope_correlation.toFixed(3) : 'N/A'}
          sub="mid↔high band r"
        />
        <Metric label={t.antiSpoof.fakeNoise} value={data.fake_noise_injected ? t.antiSpoof.yes : t.antiSpoof.no} />
      </div>

      {/* Hole ratio bar */}
      <div>
        <div className="flex justify-between text-[11px] mb-1 text-slate-400">
          <span>{t.antiSpoof.holesRatio}</span>
          <span className="font-semibold mono">{(data.spectral_holes_ratio * 100).toFixed(1)}%</span>
        </div>
        <div className="h-2 rounded-full overflow-hidden" style={{ background: 'rgba(255,255,255,0.06)' }}>
          <div
            className="h-full rounded-full"
            style={{
              width: `${Math.min(100, ((data.spectral_holes_ratio * 100) / 0.38) * 100)}%`,
              background: data.holes_detected
                ? 'linear-gradient(90deg, #f59e0b, #ef4444)'
                : 'linear-gradient(90deg, #3b82f6, #00e5ff)',
              transition: 'width 0.8s ease',
            }}
          />
        </div>
      </div>

      <div
        className={`text-[11px] leading-relaxed p-3 rounded-xl border ${
          isOk
            ? 'border-slate-800/80 bg-slate-900/60 text-slate-300'
            : 'border-2 border-rose-500/40 bg-rose-950/50 text-rose-200 font-medium shadow-inner'
        }`}
      >
        {!isOk && (
          <span className="flex items-center gap-1.5 text-rose-400 font-bold uppercase text-[10px] tracking-wider mb-1">
            <AlertTriangle size={13} className="stroke-[2.5]" />
            {t.statusBadges.anomalyAlert}
          </span>
        )}
        <p>{localizedDetail}</p>
      </div>
    </div>
  );
}

// ── Pillar 4: Ultrasonic ──────────────────────────────────────────────────────
function UltrasonicCard({
  data,
  t,
  lang,
  onExplain,
}: {
  data: UltrasonicData;
  t: typeof translations['en']['pillars'];
  lang: Language;
  onExplain: (key: ExplanationKey) => void;
}) {
  const isOk = !data.fake_hires_upsampled && data.has_true_ultrasonic_transients !== false;
  const localizedDetail = localizeUltrasonicDetail(data, lang);

  return (
    <div
      className={`card p-5 fade-in flex flex-col gap-4 transition-all duration-300 ${
        !data.applicable
          ? 'border-slate-800/80'
          : isOk
          ? 'border-slate-800/80 hover:border-slate-700/80'
          : 'border-2 border-rose-500/70 bg-gradient-to-b from-rose-950/35 via-slate-900/90 to-slate-900 shadow-[0_0_25px_rgba(244,63,94,0.2)] ring-1 ring-rose-500/30'
      }`}
      id="pillar-ultrasonic"
    >
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <div className="flex items-center gap-2">
          <div
            className="w-8 h-8 rounded-lg flex items-center justify-center"
            style={{ background: 'rgba(16, 185, 129, 0.15)', border: '1px solid rgba(16, 185, 129, 0.3)' }}
          >
            <Zap size={16} style={{ color: 'var(--accent-green)' }} />
          </div>
          <span className="font-bold text-sm sm:text-base text-slate-100">{t.ultrasonic.title}</span>
        </div>
        <div className="flex items-center gap-1.5">
          <button
            onClick={() => onExplain('ultrasonic')}
            className="flex items-center gap-1 text-[11px] font-semibold px-2.5 py-1 rounded-full bg-cyan-500/10 hover:bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 transition-all cursor-pointer shadow-sm hover:scale-105 active:scale-95"
            title={translations[lang].explanationsBtn}
          >
            <HelpCircle size={12} className="shrink-0 text-cyan-400" />
            <span>{translations[lang].explanationsBtn}</span>
          </button>
          <StatusBadge ok={isOk} na={!data.applicable} badges={t.statusBadges} />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <Metric label={t.ultrasonic.applicable} value={data.applicable ? t.ultrasonic.applicableYes : t.ultrasonic.applicableNo} />
        <Metric
          label={t.ultrasonic.upsampled}
          value={!data.applicable ? '—' : data.fake_hires_upsampled ? t.ultrasonic.yes : t.ultrasonic.no}
        />
        <Metric
          label={t.ultrasonic.ultrasonicHarmonics}
          value={
            data.has_true_ultrasonic_transients == null
              ? t.ultrasonic.notAvailable
              : data.has_true_ultrasonic_transients
              ? t.ultrasonic.genuine
              : t.ultrasonic.suspicious
          }
        />
        <Metric
          label={t.ultrasonic.correlation}
          value={data.ultrasonic_correlation != null ? data.ultrasonic_correlation.toFixed(3) : t.ultrasonic.notAvailable}
        />
      </div>

      <div
        className={`text-[11px] leading-relaxed p-3 rounded-xl border ${
          !data.applicable || isOk
            ? 'border-slate-800/80 bg-slate-900/60 text-slate-300'
            : 'border-2 border-rose-500/40 bg-rose-950/50 text-rose-200 font-medium shadow-inner'
        }`}
      >
        {data.applicable && !isOk && (
          <span className="flex items-center gap-1.5 text-rose-400 font-bold uppercase text-[10px] tracking-wider mb-1">
            <AlertTriangle size={13} className="stroke-[2.5]" />
            {t.statusBadges.anomalyAlert}
          </span>
        )}
        <p>{localizedDetail}</p>
      </div>
    </div>
  );
}

// ── Grid ─────────────────────────────────────────────────────────────────────
export function MetricsGrid({ bitDepth, spectral, antiSpoof, ultrasonic, t, lang = 'vi' }: Props) {
  const [explainKey, setExplainKey] = useState<ExplanationKey | null>(null);

  return (
    <>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-5">
        <BitDepthCard data={bitDepth} spectral={spectral} t={t} lang={lang} onExplain={setExplainKey} />
        <SpectralCutoffCard data={spectral} t={t} lang={lang} onExplain={setExplainKey} />
        <AntiSpoofCard data={antiSpoof} t={t} lang={lang} onExplain={setExplainKey} />
        <UltrasonicCard data={ultrasonic} t={t} lang={lang} onExplain={setExplainKey} />
      </div>

      <ExplainModal
        metricKey={explainKey}
        onClose={() => setExplainKey(null)}
        t={translations[lang]}
        lang={lang}
      />
    </>
  );
}
