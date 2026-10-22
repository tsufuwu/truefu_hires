// App.tsx — Main TrueLossless Inspector application with bilingual support (Vietnamese default)
import { useState, useCallback, useEffect } from 'react';
import {
  RefreshCw,
  AlertCircle,
  Sparkles,
  Binary,
  Scissors,
  ShieldAlert,
  Zap,
  Play,
  HelpCircle,
} from 'lucide-react';
import {
  analyzeFile,
  analyzeSample,
  getSamples,
  API_BASE,
  type AnalysisResult,
  type DemoSample,
} from './api';
import { translations, type Language } from './i18n';
import { LanguageSwitch } from './components/LanguageSwitch';
import { UploadZone } from './components/UploadZone';
import { SignalMonitor } from './components/SignalMonitor';
import { VerdictBanner } from './components/VerdictBanner';
import { MetricsGrid } from './components/MetricsGrid';
import { AdvancedGrid } from './components/AdvancedGrid';
import { RolloffChart } from './components/RolloffChart';
import { SpectrogramModal } from './components/SpectrogramModal';
import { ExplainModal, type ExplanationKey } from './components/ExplainModal';
import logoImg from './assets/logo.png';

type State =
  | { phase: 'idle' }
  | { phase: 'loading'; currentTarget?: string }
  | { phase: 'done'; result: AnalysisResult }
  | { phase: 'error'; message: string };

export default function App() {
  // Vietnamese ('vi') is the default language
  const [lang, setLang] = useState<Language>(() => {
    const saved = localStorage.getItem('lossless_lang') as Language;
    return saved === 'en' ? 'en' : 'vi';
  });

  const [state, setState] = useState<State>({ phase: 'idle' });
  const [samples, setSamples] = useState<DemoSample[]>([]);
  const [loadingSampleId, setLoadingSampleId] = useState<string | null>(null);
  const [explainKey, setExplainKey] = useState<ExplanationKey | null>(null);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);

  const t = translations[lang];

  const handleLanguageChange = (newLang: Language) => {
    setLang(newLang);
    localStorage.setItem('lossless_lang', newLang);
  };

  useEffect(() => {
    getSamples().then(setSamples).catch(() => {});
  }, []);

  const handleFile = useCallback(async (file: File) => {
    if (audioUrl && audioUrl.startsWith('blob:')) {
      URL.revokeObjectURL(audioUrl);
    }
    const localUrl = URL.createObjectURL(file);
    setAudioUrl(localUrl);

    setState({ phase: 'loading', currentTarget: file.name });
    try {
      const result = await analyzeFile(file);
      setState({ phase: 'done', result });
    } catch (err: any) {
      setState({ phase: 'error', message: err.message || 'Analysis failed' });
    }
  }, [audioUrl]);

  const handleSelectSample = useCallback(async (sampleId: string, sampleTitle: string) => {
    if (audioUrl && audioUrl.startsWith('blob:')) {
      URL.revokeObjectURL(audioUrl);
    }
    setAudioUrl(`${API_BASE}/api/sample-audio/${encodeURIComponent(sampleId)}`);

    setLoadingSampleId(sampleId);
    setState({ phase: 'loading', currentTarget: sampleTitle });
    try {
      const result = await analyzeSample(sampleId);
      setState({ phase: 'done', result });
    } catch (err: any) {
      setState({ phase: 'error', message: err.message || 'Sample analysis failed' });
    } finally {
      setLoadingSampleId(null);
    }
  }, [audioUrl]);

  const reset = () => {
    if (audioUrl && audioUrl.startsWith('blob:')) {
      URL.revokeObjectURL(audioUrl);
    }
    setAudioUrl(null);
    setState({ phase: 'idle' });
  };

  const pillarCards: {
    key: 'bitDepth' | 'spectralCutoff' | 'antiSpoof' | 'ultrasonic';
    icon: any;
    color: string;
    title: string;
    desc: string;
  }[] = [
    {
      key: 'bitDepth',
      icon: Binary,
      color: '#3b82f6',
      title: t.pillarsShowcase.p1Title,
      desc: t.pillarsShowcase.p1Desc,
    },
    {
      key: 'spectralCutoff',
      icon: Scissors,
      color: '#00e5ff',
      title: t.pillarsShowcase.p2Title,
      desc: t.pillarsShowcase.p2Desc,
    },
    {
      key: 'antiSpoof',
      icon: ShieldAlert,
      color: '#f59e0b',
      title: t.pillarsShowcase.p3Title,
      desc: t.pillarsShowcase.p3Desc,
    },
    {
      key: 'ultrasonic',
      icon: Zap,
      color: '#10b981',
      title: t.pillarsShowcase.p4Title,
      desc: t.pillarsShowcase.p4Desc,
    },
  ];

  return (
    <div className="relative min-h-screen flex flex-col justify-between" style={{ background: 'var(--bg-base)' }}>
      {/* Background ambient lighting with dynamic living aurora (Requirement 4) */}
      <div className="ambient-glow-wrapper">
        <div className="aurora-glow-1" />
        <div className="aurora-glow-2" />
        <div className="aurora-glow-3" />
      </div>
      <div className="bg-grid-pattern" />

      {/* ── Top Header Navigation ──────────────────────────────────── */}
      <header
        className="relative z-20 flex flex-wrap items-center justify-between gap-4 px-6 sm:px-10 py-4"
        style={{
          borderBottom: '1px solid rgba(99, 130, 201, 0.12)',
          background: 'rgba(6, 8, 14, 0.8)',
          backdropFilter: 'blur(16px)',
        }}
      >
        {/* Brand / Logo */}
        <div className="flex items-center gap-3 cursor-pointer group" onClick={reset}>
          <div className="relative h-10 w-auto rounded-xl flex items-center justify-center transition-transform group-hover:scale-105">
            <img
              src={logoImg}
              alt="Truefu Hires Logo"
              className="h-10 w-auto max-w-[55px] object-contain rounded-lg drop-shadow-[0_0_12px_rgba(0,229,255,0.4)]"
            />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-base font-bold tracking-tight text-slate-100 group-hover:text-cyan-300 transition-colors">
                {t.header.title}
              </span>
              <span className="hidden sm:inline-block text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-md bg-blue-500/10 text-cyan-400 border border-cyan-500/20">
                {t.header.dspVersion}
              </span>
            </div>
            <p className="text-xs text-slate-400">{t.header.subtitle}</p>
          </div>
        </div>

        {/* Right side controls: Reset + Engine Status + Language Switch */}
        <div className="flex items-center gap-3">
          {state.phase !== 'idle' && (
            <button
              id="analyze-another-btn"
              onClick={reset}
              className="flex items-center gap-1.5 text-xs sm:text-sm px-3.5 py-1.5 rounded-xl transition-all font-semibold"
              style={{
                background: 'rgba(59, 130, 246, 0.12)',
                color: 'var(--accent-cyan)',
                border: '1px solid rgba(0, 229, 255, 0.3)',
              }}
              onMouseEnter={e => {
                e.currentTarget.style.background = 'rgba(0, 229, 255, 0.2)';
                e.currentTarget.style.borderColor = 'rgba(0, 229, 255, 0.5)';
              }}
              onMouseLeave={e => {
                e.currentTarget.style.background = 'rgba(59, 130, 246, 0.12)';
                e.currentTarget.style.borderColor = 'rgba(0, 229, 255, 0.3)';
              }}
            >
              <RefreshCw size={14} />
              <span>{t.header.inspectAnother}</span>
            </button>
          )}

          <div
            className="hidden md:flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-full font-medium"
            style={{
              background: 'rgba(16, 185, 129, 0.08)',
              border: '1px solid rgba(16, 185, 129, 0.25)',
              color: 'var(--accent-green)',
            }}
          >
            <span
              className="pulse-dot w-2 h-2 rounded-full inline-block"
              style={{ background: 'var(--accent-green)' }}
            />
            <span>{t.header.engineReady}</span>
          </div>

          {/* Language Switcher in top right corner */}
          <LanguageSwitch currentLang={lang} onLanguageChange={handleLanguageChange} />
        </div>
      </header>

      {/* ── Main content area (Expanded width to utilize screen space) ──── */}
      <main className="relative z-10 flex-1 max-w-[1540px] 2xl:max-w-[1640px] w-full mx-auto px-4 sm:px-8 py-5 flex flex-col justify-center">

        {/* ── IDLE PHASE ────────────────────────────────────────────── */}
        {state.phase === 'idle' && (
          <div className="fade-in flex flex-col items-center">
            {/* Hero Header */}
            <div className="text-center max-w-2xl mx-auto mb-8 flex flex-col items-center">
              <div
                className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full text-xs font-semibold tracking-wide border mb-4"
                style={{
                  background: 'rgba(0, 229, 255, 0.06)',
                  borderColor: 'rgba(0, 229, 255, 0.25)',
                  color: 'var(--accent-cyan)',
                  boxShadow: '0 0 20px rgba(0, 229, 255, 0.12)',
                }}
              >
                <Sparkles size={13} className="text-cyan-400" />
                <span>{t.hero.badge}</span>
              </div>

              <h2
                className="text-3xl sm:text-5xl font-extrabold tracking-tight mb-3"
                style={{
                  background: 'linear-gradient(135deg, #ffffff 20%, #93c5fd 60%, #00e5ff 100%)',
                  WebkitBackgroundClip: 'text',
                  WebkitTextFillColor: 'transparent',
                }}
              >
                {t.hero.titlePrefix}
                <span className="bg-gradient-to-r from-blue-400 via-cyan-300 to-emerald-400 bg-clip-text text-transparent">
                  {t.hero.titleHighlight}
                </span>
              </h2>

              <p className="text-sm sm:text-base text-slate-400 leading-relaxed max-w-xl mx-auto">
                {t.hero.description}
              </p>
            </div>

            {/* 1. PRIMARY ACTION: FILE UPLOAD ZONE AT THE TOP (NO CLUTTER) */}
            <div className="w-full mb-6">
              <UploadZone onFile={handleFile} isLoading={false} t={t.upload} />
            </div>

            {/* 2. COMPACT AUDIOPHILE SIGNAL MONITOR (DUAL STEREO VU METERS) */}
            <div className="w-full mb-8">
              <SignalMonitor isLoading={false} lang={lang} />
            </div>

            {/* 3. Quick Demo Test Samples Row */}
            {samples.length > 0 && (
              <div className="w-full max-w-2xl mx-auto mb-10 p-4 rounded-2xl border border-slate-800/80 bg-slate-900/40 backdrop-blur-md">
                <div className="flex items-center gap-2 mb-3 px-1 text-xs font-semibold uppercase tracking-wider text-slate-400">
                  <Play size={12} className="text-cyan-400" />
                  <span>{t.demo.title}</span>
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                  {samples.map(sample => {
                    const isSelected = loadingSampleId === sample.id;
                    const sampleTrans = (t.demo.samples as Record<string, { title: string; badge: string }>)[sample.id];
                    const sampleTitle = sampleTrans?.title || sample.title;
                    const sampleBadge = sampleTrans?.badge || sample.badge;

                    const dotColor =
                      sample.type === 'authentic'
                        ? 'var(--accent-green)'
                        : sample.type === 'padded'
                        ? 'var(--accent-amber)'
                        : sample.type === 'fake'
                        ? 'var(--accent-red)'
                        : 'var(--accent-purple)';

                    return (
                      <button
                        key={sample.id}
                        onClick={() => handleSelectSample(sample.id, sampleTitle)}
                        disabled={isSelected}
                        className="group flex flex-col text-left p-2.5 rounded-xl transition-all border border-slate-800 hover:border-cyan-500/40 hover:bg-slate-800/60 cursor-pointer"
                        style={{
                          background: 'rgba(255, 255, 255, 0.02)',
                        }}
                      >
                        <div className="flex items-center gap-1.5 mb-1">
                          <span
                            className="w-2 h-2 rounded-full shrink-0"
                            style={{ background: dotColor, boxShadow: `0 0 6px ${dotColor}` }}
                          />
                          <span className="text-xs font-semibold text-slate-200 truncate group-hover:text-cyan-300">
                            {sampleTitle}
                          </span>
                        </div>
                        <span className="text-[10px] text-slate-500 truncate">
                          {sampleBadge}
                        </span>
                      </button>
                    );
                  })}
                </div>
              </div>
            )}

            {/* 4. 4 Pillars Feature Cards Grid */}
            <div className="w-full max-w-5xl mx-auto">
              <div className="text-center mb-4">
                <span className="text-xs font-bold uppercase tracking-widest text-slate-500">
                  {t.pillarsShowcase.heading}
                </span>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                {pillarCards.map((pillar, idx) => {
                  const Icon = pillar.icon;
                  return (
                    <button
                      key={idx}
                      type="button"
                      onClick={() => setExplainKey(pillar.key)}
                      className="card p-4 flex flex-col gap-2.5 transition-all duration-200 hover:-translate-y-1 hover:border-cyan-500/50 hover:shadow-[0_8px_24px_rgba(6,182,212,0.15)] text-left group cursor-pointer relative"
                      style={{
                        background: 'rgba(15, 22, 35, 0.75)',
                        borderColor: 'rgba(99, 130, 201, 0.16)',
                      }}
                    >
                      <div className="flex items-center justify-between gap-2">
                        <div className="flex items-center gap-2.5">
                          <div
                            className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0 transition-transform group-hover:scale-110"
                            style={{
                              background: `${pillar.color}18`,
                              border: `1px solid ${pillar.color}35`,
                            }}
                          >
                            <Icon size={16} style={{ color: pillar.color }} />
                          </div>
                          <h4 className="text-xs font-bold text-slate-200 tracking-tight group-hover:text-cyan-300 transition-colors">
                            {pillar.title}
                          </h4>
                        </div>
                        <span className="text-[10px] font-semibold text-cyan-400 bg-cyan-500/10 px-2 py-0.5 rounded-full border border-cyan-500/25 group-hover:bg-cyan-500/20 group-hover:border-cyan-500/40 transition-all flex items-center gap-1 shrink-0">
                          <HelpCircle size={10} />
                          <span>{t.explanationsBtn}</span>
                        </span>
                      </div>
                      <p className="text-[11px] text-slate-400 leading-relaxed group-hover:text-slate-300 transition-colors">
                        {pillar.desc}
                      </p>
                      <div className="mt-auto pt-1 flex items-center text-[10px] font-medium text-cyan-400/70 group-hover:text-cyan-300 group-hover:translate-x-0.5 transition-all">
                        <span>{lang === 'vi' ? 'Bấm để xem giải thích chi tiết' : 'Click to view explanation'} &rarr;</span>
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>
          </div>
        )}

        {/* ── LOADING PHASE ─────────────────────────────────────────── */}
        {state.phase === 'loading' && (
          <div className="fade-in py-8 flex flex-col items-center w-full gap-5">
            <UploadZone onFile={() => {}} isLoading={true} t={t.upload} />
            <SignalMonitor
              isLoading={true}
              currentTarget={state.currentTarget}
              lang={lang}
            />
          </div>
        )}

        {/* ── ERROR PHASE ───────────────────────────────────────────── */}
        {state.phase === 'error' && (
          <div className="fade-in max-w-xl mx-auto w-full">
            <div
              className="card p-6 flex flex-col sm:flex-row items-start gap-4 border"
              style={{
                borderColor: 'rgba(244, 63, 94, 0.35)',
                background: 'rgba(244, 63, 94, 0.08)',
              }}
            >
              <AlertCircle
                size={24}
                className="shrink-0 mt-0.5"
                style={{ color: 'var(--accent-red)' }}
              />
              <div className="flex-1">
                <h3 className="font-bold text-base text-rose-400 mb-1">
                  {t.error.title}
                </h3>
                <p className="text-sm text-slate-300 mb-3">{state.message}</p>
                <p className="text-xs text-slate-500 mb-4">{t.error.tip}</p>
                <button
                  onClick={reset}
                  className="px-4 py-2 rounded-xl text-xs font-bold uppercase tracking-wider text-rose-300 border border-rose-500/40 bg-rose-500/10 hover:bg-rose-500/20 transition-all"
                >
                  {t.error.tryAnother}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* ── DONE RESULTS PHASE ────────────────────────────────────── */}
        {state.phase === 'done' && (() => {
          const { result } = state;
          return (
            <div className="fade-in flex flex-col gap-4 sm:gap-5 w-full">
              {/* Verdict Banner with Mini Audio Player */}
              <VerdictBanner
                verdict={result.verdict}
                metadata={result.metadata}
                filename={result.filename}
                t={t.verdict}
                lang={lang}
                audioUrl={audioUrl}
              />

              {/* 4-Pillar Diagnostics Cards */}
              <MetricsGrid
                bitDepth={result.pillars.bit_depth}
                spectral={result.pillars.spectral_cutoff}
                antiSpoof={result.pillars.anti_spoof}
                ultrasonic={result.pillars.ultrasonic}
                t={t.pillars}
                lang={lang}
              />

              {/* Advanced 4-Pillar Anti-Spoofing & Verification Modules */}
              {result.advanced && (
                <AdvancedGrid
                  advanced={result.advanced}
                  t={t.advanced}
                  lang={lang}
                />
              )}

              {/* Dual Visual Panel */}
              <div className="grid grid-cols-1 xl:grid-cols-2 gap-5">
                <RolloffChart
                  data={result.visuals.rolloff_curve}
                  detectedCutoffHz={result.pillars.spectral_cutoff.detected_cutoff_hz}
                  t={t.visuals}
                />
                <SpectrogramModal
                  base64={result.visuals.spectrogram_base64}
                  detectedCutoffHz={result.pillars.spectral_cutoff.detected_cutoff_hz}
                  t={t.visuals}
                />
              </div>

              {/* Quick Drop Zone at bottom */}
              <div className="pt-4 pb-2 max-w-xl mx-auto w-full">
                <div className="text-center mb-2">
                  <span className="text-xs font-semibold text-slate-400">
                    {t.bottomUpload}
                  </span>
                </div>
                <UploadZone onFile={handleFile} isLoading={false} t={t.upload} />
              </div>
            </div>
          );
        })()}
      </main>

      {/* ── Bottom Footer ───────────────────────────────────────────── */}
      <footer
        className="relative z-10 text-center py-6 px-4 text-xs text-slate-500"
        style={{ borderTop: '1px solid rgba(99, 130, 201, 0.1)' }}
      >
        <div className="max-w-6xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-3">
          <div className="flex items-center gap-2.5">
            <img src={logoImg} alt="Logo" className="h-4 w-auto object-contain opacity-80" />
            <span>
              <strong className="text-slate-400">{t.footer.brand}</strong> · {t.footer.tech}
            </span>
          </div>
          <span className="text-slate-600">
            {t.footer.sub}
          </span>
        </div>
      </footer>

      {/* ── Educational Explanations Modal ──────────────────────────── */}
      <ExplainModal
        metricKey={explainKey}
        onClose={() => setExplainKey(null)}
        t={t}
        lang={lang}
      />
    </div>
  );
}
