// components/ExplainModal.tsx — Layman Educational Modal for Truefu Hires
import { useEffect } from 'react';
import { createPortal } from 'react-dom';
import {
  X,
  Lightbulb,
  Headphones,
  Search,
  CheckCircle2,
  Sparkles,
} from 'lucide-react';
import type { Language, translations } from '../i18n';

export type ExplanationKey =
  | 'bitDepth'
  | 'spectralCutoff'
  | 'antiSpoof'
  | 'ultrasonic'
  | 'phaseCoherence'
  | 'naturalDecay'
  | 'accurateRip'
  | 'aiArtifacts';

interface Props {
  metricKey: ExplanationKey | null;
  onClose: () => void;
  t: typeof translations['vi'];
  lang: Language;
}

export function ExplainModal({ metricKey, onClose, t, lang }: Props) {
  // Close on Escape key and prevent background scroll
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    if (metricKey) {
      window.addEventListener('keydown', handleKeyDown);
      document.body.style.overflow = 'hidden';
    }
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      document.body.style.overflow = '';
    };
  }, [metricKey, onClose]);

  if (!metricKey) return null;

  const item = t.explanations[metricKey];
  if (!item) return null;

  const sections = t.explanationsSections;

  return createPortal(
    <div
      className="fixed inset-0 z-[9999] flex items-center justify-center p-4 sm:p-6 bg-black/85 backdrop-blur-md"
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        width: '100vw',
        height: '100vh',
      }}
      onClick={onClose}
    >
      <div
        className="relative max-w-2xl w-full bg-slate-900 border border-white/20 rounded-3xl p-6 sm:p-8 shadow-[0_25px_60px_rgba(0,0,0,0.95)] overflow-hidden flex flex-col max-h-[85vh] my-auto"
        onClick={(e) => e.stopPropagation()}
        style={{
          background: 'linear-gradient(180deg, rgba(15, 23, 42, 0.98) 0%, rgba(10, 15, 29, 0.98) 100%)',
        }}
      >
        {/* Subtle Ambient Radial Glow */}
        <div className="absolute top-0 right-0 w-72 h-72 bg-cyan-500/10 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute bottom-0 left-0 w-72 h-72 bg-blue-600/10 rounded-full blur-3xl pointer-events-none" />

        {/* Top Header */}
        <div className="flex items-start justify-between gap-4 pb-4 border-b border-white/10 shrink-0">
          <div className="flex items-center gap-3 min-w-0">
            <div className="w-11 h-11 rounded-2xl flex items-center justify-center bg-cyan-500/15 border border-cyan-400/30 text-cyan-300 shrink-0 shadow-[0_0_15px_rgba(6,182,212,0.25)]">
              <Sparkles size={22} className="stroke-[2.2]" />
            </div>
            <div className="min-w-0">
              <div className="flex items-center gap-2 flex-wrap mb-1">
                <span className="text-[11px] font-semibold tracking-wider uppercase px-2.5 py-0.5 rounded-full bg-cyan-950/80 border border-cyan-500/30 text-cyan-300">
                  {lang === 'vi' ? 'Giải thích cho người nghe nhạc' : 'Audiophile Layman Guide'}
                </span>
              </div>
              <h3 className="text-lg sm:text-xl font-bold text-white tracking-tight leading-snug">
                {item.title}
              </h3>
              <p className="text-xs sm:text-sm text-slate-400 font-medium">
                {item.subtitle}
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-2 rounded-xl bg-slate-800/80 hover:bg-white/15 text-slate-400 hover:text-white transition-all shrink-0 border border-white/5 cursor-pointer"
            title={lang === 'vi' ? 'Đóng' : 'Close'}
          >
            <X size={18} />
          </button>
        </div>

        {/* Scrollable Explanations Content */}
        <div
          className="overflow-y-auto pr-2 py-4 space-y-4 flex-1"
          style={{ overscrollBehavior: 'contain' }}
        >
          {/* Section 1: Nó là gì? */}
          <div className="p-4 rounded-2xl border border-amber-500/25 bg-amber-950/20 shadow-sm">
            <div className="flex items-center gap-2 mb-2 text-amber-300 font-bold text-xs uppercase tracking-wide">
              <Lightbulb size={16} className="text-amber-400" />
              <span>{sections.what}</span>
            </div>
            <p className="text-xs sm:text-sm text-slate-200 leading-relaxed font-normal">
              {item.whatIsIt}
            </p>
          </div>

          {/* Section 2: Ảnh hưởng gì tới nhạc lossless? */}
          <div className="p-4 rounded-2xl border border-rose-500/25 bg-rose-950/20 shadow-sm">
            <div className="flex items-center gap-2 mb-2 text-rose-300 font-bold text-xs uppercase tracking-wide">
              <Headphones size={16} className="text-rose-400" />
              <span>{sections.why}</span>
            </div>
            <p className="text-xs sm:text-sm text-slate-200 leading-relaxed font-normal">
              {item.whyItMatters}
            </p>
          </div>

          {/* Section 3: Truefu Hires kiểm tra như thế nào? */}
          <div className="p-4 rounded-2xl border border-sky-500/25 bg-sky-950/20 shadow-sm">
            <div className="flex items-center gap-2 mb-2 text-sky-300 font-bold text-xs uppercase tracking-wide">
              <Search size={16} className="text-sky-400" />
              <span>{sections.how}</span>
            </div>
            <p className="text-xs sm:text-sm text-slate-200 leading-relaxed font-normal">
              {item.howWeCheck}
            </p>
          </div>

          {/* Section 4: Dấu hiệu chuẩn xịn */}
          <div className="p-4 rounded-2xl border border-emerald-500/30 bg-emerald-950/20 shadow-sm">
            <div className="flex items-center gap-2 mb-2 text-emerald-300 font-bold text-xs uppercase tracking-wide">
              <CheckCircle2 size={16} className="text-emerald-400" />
              <span>{sections.ideal}</span>
            </div>
            <p className="text-xs sm:text-sm text-emerald-100/90 leading-relaxed font-medium">
              {item.idealSign}
            </p>
          </div>
        </div>

        {/* Modal Footer */}
        <div className="pt-4 border-t border-white/10 flex items-center justify-between gap-3 shrink-0">
          <span className="text-[11px] text-slate-500 hidden sm:inline">
            Truefu Hires · Digital Signal Processing Engine
          </span>
          <button
            onClick={onClose}
            className="w-full sm:w-auto px-6 py-2.5 rounded-xl font-semibold text-xs tracking-wide bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-slate-950 shadow-[0_0_20px_rgba(6,182,212,0.35)] transition-all cursor-pointer"
          >
            {t.explanationsModalClose}
          </button>
        </div>
      </div>
    </div>,
    document.body
  );
}
