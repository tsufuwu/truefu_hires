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
  Heart,
  ListMusic,
  Clock,
  CheckCircle2,
  XCircle,
} from 'lucide-react';
import {
  analyzeFile,
  analyzeFiles,
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

// Seconds per file estimate on free-tier backend
const SEC_PER_FILE_SHORT = 8;   // < 3 min
const SEC_PER_FILE_LONG  = 15;  // >= 3 min

function estimateSeconds(files: File[]): number {
  return files.reduce((acc, f) => {
    const estimatedDurationMin = (f.size / (1024 * 1024)) * 2; // rough: 1 MB ≈ 2 min of FLAC
    return acc + (estimatedDurationMin < 3 ? SEC_PER_FILE_SHORT : SEC_PER_FILE_LONG);
  }, 0);
}

function formatEta(seconds: number): string {
  if (seconds < 60) return `~${seconds}s`;
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return s > 0 ? `~${m}m ${s}s` : `~${m}m`;
}

type BatchItem =
  | { status: 'pending'; filename: string }
  | { status: 'processing'; filename: string }
  | { status: 'done'; filename: string; result: AnalysisResult }
  | { status: 'error'; filename: string; error: string };

type State =
  | { phase: 'idle' }
  | { phase: 'loading'; currentTarget?: string }
  | { phase: 'batch_loading'; items: BatchItem[]; eta: number; currentIndex: number }
  | { phase: 'batch_done'; items: BatchItem[] }
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
  const [activeBatchIdx, setActiveBatchIdx] = useState<number>(0);

  const t = translations[lang];

  const handleLanguageChange = (newLang: Language) => {
    setLang(newLang);
    localStorage.setItem('lossless_lang', newLang);
  };

  useEffect(() => {
    getSamples().then(setSamples).catch(() => {});
  }, []);

  useEffect(() => {
    if (state.phase === 'batch_done') {
      const firstDone = state.items.findIndex(i => i.status === 'done');
      setActiveBatchIdx(firstDone >= 0 ? firstDone : 0);
    }
  }, [state.phase]);

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

  const handleFiles = useCallback(async (files: File[]) => {
    if (files.length === 1) {
      handleFile(files[0]);
      return;
    }
    // Batch mode
    if (audioUrl && audioUrl.startsWith('blob:')) {
      URL.revokeObjectURL(audioUrl);
    }
    setAudioUrl(null);
    const etaSec = estimateSeconds(files);
    const initialItems: BatchItem[] = files.map(f => ({ status: 'pending', filename: f.name }));
    setState({ phase: 'batch_loading', items: initialItems, eta: etaSec, currentIndex: 0 });

    // Process files sequentially on frontend using analyzeFiles (backend also processes sequentially)
    try {
      const batchResults = await analyzeFiles(files);
      const doneItems: BatchItem[] = batchResults.map((r) => {
        if ('error' in r) {
          return { status: 'error', filename: r.filename, error: r.error };
        }
        return { status: 'done', filename: r.filename, result: r as AnalysisResult };
      });
      setState({ phase: 'batch_done', items: doneItems });
    } catch (err: any) {
      setState({ phase: 'error', message: err.message || 'Batch analysis failed' });
    }
  }, [audioUrl, handleFile]);

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

          {/* Donate Button */}
          <a
            id="donate-btn"
            href="https://tsufu.gitbook.io/donate"
            target="_blank"
            rel="noopener noreferrer"
            title={t.header.donateTooltip}
            className="flex items-center gap-1.5 text-xs sm:text-sm px-3 py-1.5 rounded-xl transition-all font-semibold group cursor-pointer"
            style={{
              background: 'linear-gradient(135deg, rgba(244, 63, 94, 0.12), rgba(236, 72, 153, 0.08))',
              border: '1px solid rgba(244, 63, 94, 0.35)',
              color: '#fda4af',
              boxShadow: '0 0 14px rgba(244, 63, 94, 0.12)',
            }}
            onMouseEnter={e => {
              e.currentTarget.style.background = 'linear-gradient(135deg, rgba(244, 63, 94, 0.25), rgba(236, 72, 153, 0.18))';
              e.currentTarget.style.borderColor = 'rgba(244, 63, 94, 0.6)';
              e.currentTarget.style.boxShadow = '0 0 20px rgba(244, 63, 94, 0.3)';
              e.currentTarget.style.transform = 'translateY(-1px)';
            }}
            onMouseLeave={e => {
              e.currentTarget.style.background = 'linear-gradient(135deg, rgba(244, 63, 94, 0.12), rgba(236, 72, 153, 0.08))';
              e.currentTarget.style.borderColor = 'rgba(244, 63, 94, 0.35)';
              e.currentTarget.style.boxShadow = '0 0 14px rgba(244, 63, 94, 0.12)';
              e.currentTarget.style.transform = 'translateY(0)';
            }}
          >
            <Heart size={14} className="text-rose-400 fill-rose-400/40 group-hover:scale-110 group-hover:fill-rose-400 transition-all duration-200" />
            <span>{t.header.donate}</span>
          </a>

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
              <UploadZone onFile={handleFile} onFiles={handleFiles} isLoading={false} t={t.upload} />
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

        {/* ── BATCH LOADING PHASE ────────────────────────────────────── */}
        {state.phase === 'batch_loading' && (
          <div className="fade-in py-8 flex flex-col items-center w-full gap-6">
            <div className="w-full max-w-2xl">
              {/* ETA Banner */}
              <div
                className="flex items-center justify-between gap-3 px-5 py-3 rounded-2xl mb-5"
                style={{
                  background: 'rgba(0, 229, 255, 0.06)',
                  border: '1px solid rgba(0, 229, 255, 0.2)',
                }}
              >
                <div className="flex items-center gap-2">
                  <ListMusic size={18} className="text-cyan-400" />
                  <span className="text-sm font-bold text-slate-200">
                    Đang phân tích {state.items.length} file nhạc...
                  </span>
                </div>
                <div className="flex items-center gap-1.5 text-xs text-cyan-300 font-semibold">
                  <Clock size={13} />
                  <span>Dự kiến hoàn tất: {formatEta(state.eta)}</span>
                </div>
              </div>

              {/* File Queue */}
              <div className="flex flex-col gap-2">
                {state.items.map((item, idx) => (
                  <div
                    key={idx}
                    className="flex items-center gap-3 px-4 py-3 rounded-xl"
                    style={{
                      background: idx === state.currentIndex
                        ? 'rgba(0, 229, 255, 0.08)'
                        : 'rgba(255, 255, 255, 0.02)',
                      border: idx === state.currentIndex
                        ? '1px solid rgba(0, 229, 255, 0.3)'
                        : '1px solid rgba(99, 130, 201, 0.12)',
                    }}
                  >
                    <div className="w-5 h-5 shrink-0 flex items-center justify-center">
                      {item.status === 'processing' ? (
                        <div className="w-4 h-4 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin" />
                      ) : item.status === 'done' ? (
                        <CheckCircle2 size={16} className="text-emerald-400" />
                      ) : item.status === 'error' ? (
                        <XCircle size={16} className="text-rose-400" />
                      ) : (
                        <div className="w-2 h-2 rounded-full bg-slate-600" />
                      )}
                    </div>
                    <span className="text-sm text-slate-300 truncate flex-1">{item.filename}</span>
                    <span className="text-xs text-slate-500 shrink-0">
                      {idx + 1}/{state.items.length}
                    </span>
                  </div>
                ))}
              </div>

              {/* Progress bar */}
              <div className="mt-4 w-full h-2 rounded-full overflow-hidden bg-slate-900 border border-cyan-500/20">
                <div
                  className="h-full rounded-full transition-all duration-500"
                  style={{
                    width: `${(state.currentIndex / state.items.length) * 100}%`,
                    background: 'linear-gradient(90deg, #00e5ff, #3b82f6)',
                    boxShadow: '0 0 12px rgba(0, 229, 255, 0.4)',
                  }}
                />
              </div>
            </div>
            <SignalMonitor isLoading={true} lang={lang} />
          </div>
        )}

        {/* ── BATCH DONE PHASE ──────────────────────────────────────── */}
        {state.phase === 'batch_done' && (() => {
          const successItems = state.items.filter(i => i.status === 'done');
          const errorItems = state.items.filter(i => i.status === 'error');
          const activeItem = state.items[activeBatchIdx];

          return (
            <div className="fade-in flex flex-col gap-4 w-full">
              {/* Summary Header */}
              <div
                className="flex flex-wrap items-center justify-between gap-3 px-5 py-3 rounded-2xl"
                style={{
                  background: 'rgba(16, 185, 129, 0.06)',
                  border: '1px solid rgba(16, 185, 129, 0.2)',
                }}
              >
                <div className="flex items-center gap-2">
                  <ListMusic size={18} className="text-emerald-400" />
                  <span className="text-sm font-bold text-slate-200">
                    Hoàn tất {successItems.length}/{state.items.length} file ·{' '}
                    {errorItems.length > 0 && (
                      <span className="text-rose-400">{errorItems.length} lỗi</span>
                    )}
                  </span>
                </div>
                <button
                  onClick={reset}
                  className="flex items-center gap-1.5 text-xs font-bold px-3 py-1.5 rounded-xl"
                  style={{
                    background: 'rgba(0, 229, 255, 0.1)',
                    border: '1px solid rgba(0, 229, 255, 0.3)',
                    color: 'var(--accent-cyan)',
                  }}
                >
                  <RefreshCw size={12} />
                  <span>Kiểm tra mới</span>
                </button>
              </div>

              {/* File Tabs */}
              <div className="flex flex-wrap gap-2">
                {state.items.map((item, idx) => (
                  <button
                    key={idx}
                    onClick={() => item.status === 'done' && setActiveBatchIdx(idx)}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold transition-all"
                    style={{
                      background: activeBatchIdx === idx
                        ? 'rgba(0, 229, 255, 0.15)'
                        : 'rgba(255, 255, 255, 0.03)',
                      border: activeBatchIdx === idx
                        ? '1px solid rgba(0, 229, 255, 0.4)'
                        : '1px solid rgba(99, 130, 201, 0.15)',
                      color: activeBatchIdx === idx ? '#00e5ff'
                        : item.status === 'error' ? '#fb7185' : '#94a3b8',
                      cursor: item.status === 'done' ? 'pointer' : 'default',
                    }}
                  >
                    {item.status === 'done' ? (
                      <CheckCircle2 size={12} className="text-emerald-400" />
                    ) : (
                      <XCircle size={12} className="text-rose-400" />
                    )}
                    <span className="max-w-[140px] truncate">{item.filename}</span>
                  </button>
                ))}
              </div>

              {/* Active Result */}
              {activeItem?.status === 'done' && (() => {
                const result = activeItem.result;
                return (
                  <div className="flex flex-col gap-4 w-full">
                    <VerdictBanner
                      verdict={result.verdict}
                      metadata={result.metadata}
                      filename={result.filename}
                      t={t.verdict}
                      lang={lang}
                      audioUrl={null}
                    />
                    <MetricsGrid
                      bitDepth={result.pillars.bit_depth}
                      spectral={result.pillars.spectral_cutoff}
                      antiSpoof={result.pillars.anti_spoof}
                      ultrasonic={result.pillars.ultrasonic}
                      t={t.pillars}
                      lang={lang}
                    />
                    {result.advanced && (
                      <AdvancedGrid advanced={result.advanced} t={t.advanced} lang={lang} />
                    )}
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
                  </div>
                );
              })()}

              {/* Error item display */}
              {activeItem?.status === 'error' && (
                <div
                  className="card p-5 flex items-start gap-3 border"
                  style={{ borderColor: 'rgba(244,63,94,0.3)', background: 'rgba(244,63,94,0.07)' }}
                >
                  <XCircle size={20} className="text-rose-400 shrink-0 mt-0.5" />
                  <div>
                    <p className="text-sm font-bold text-rose-400">{activeItem.filename}</p>
                    <p className="text-xs text-slate-300 mt-1">{activeItem.error}</p>
                  </div>
                </div>
              )}

              {/* Upload More */}
              <div className="pt-2 pb-2 max-w-xl mx-auto w-full">
                <UploadZone onFile={handleFile} onFiles={handleFiles} isLoading={false} t={t.upload} />
              </div>
            </div>
          );
        })()}

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
                <UploadZone onFile={handleFile} onFiles={handleFiles} isLoading={false} t={t.upload} />
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
          <div className="flex items-center gap-4">
            <a
              id="footer-donate-link"
              href="https://tsufu.gitbook.io/donate"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 text-rose-400 hover:text-rose-300 font-medium transition-colors"
            >
              <Heart size={12} className="text-rose-400 fill-rose-400/30" />
              <span>{t.footer.donate}</span>
            </a>
            <span className="text-slate-600 hidden sm:inline">·</span>
            <span className="text-slate-600">
              {t.footer.sub}
            </span>
          </div>
        </div>

        {/* Small Author Credit Line */}
        <div className="mt-3 pt-3 border-t border-slate-800/40 text-[11px] text-slate-500 font-normal">
          <span>{t.footer.credit}</span>
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
