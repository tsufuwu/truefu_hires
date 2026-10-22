// components/SpectrogramModal.tsx — Fullscreen annotated spectrogram viewer with i18n
import { useState } from 'react';
import { Maximize2, X, ImageOff } from 'lucide-react';
import type { translations } from '../i18n';

interface Props {
  base64?: string | null;
  detectedCutoffHz?: number | null;
  t: typeof translations['en']['visuals'];
}

export function SpectrogramModal({ base64, detectedCutoffHz, t }: Props) {
  const [open, setOpen] = useState(false);

  if (!base64) {
    return (
      <div className="card p-5 flex flex-col items-center justify-center gap-3 fade-in" style={{ minHeight: '220px' }}>
        <ImageOff size={32} style={{ color: 'var(--text-muted)' }} />
        <p className="text-sm text-slate-400">{t.unavailable}</p>
      </div>
    );
  }

  return (
    <>
      <div className="card p-5 fade-in relative group" id="spectrogram-card">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-bold text-slate-200">
            {t.spectrogramTitle}
            {detectedCutoffHz && (
              <span className="ml-3 text-xs font-semibold px-2 py-0.5 rounded-full mono"
                style={{ background: 'rgba(0,229,255,0.12)', color: 'var(--accent-cyan)', border: '1px solid rgba(0,229,255,0.35)' }}>
                ↑ {t.cutoffBadge}: {(detectedCutoffHz / 1000).toFixed(2)} kHz
              </span>
            )}
          </h3>
          <button
            id="spectrogram-fullscreen-btn"
            onClick={() => setOpen(true)}
            className="flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded-lg transition-all"
            style={{
              background: 'rgba(59, 130, 246, 0.12)',
              color: 'var(--accent-cyan)',
              border: '1px solid rgba(0, 229, 255, 0.25)',
            }}
            onMouseEnter={e => (e.currentTarget.style.background = 'rgba(0, 229, 255, 0.2)')}
            onMouseLeave={e => (e.currentTarget.style.background = 'rgba(59, 130, 246, 0.12)')}
          >
            <Maximize2 size={13} /> {t.fullscreenBtn}
          </button>
        </div>
        <div className="relative overflow-hidden rounded-xl" style={{ cursor: 'zoom-in' }} onClick={() => setOpen(true)}>
          <img
            src={base64}
            alt="Spectrogram"
            className="w-full block"
            style={{ borderRadius: '10px', maxHeight: '260px', objectFit: 'cover', objectPosition: 'bottom' }}
          />
          {/* Hover overlay */}
          <div className="absolute inset-0 flex items-center justify-center rounded-xl opacity-0 group-hover:opacity-100 transition-opacity"
            style={{ background: 'rgba(0,0,0,0.5)' }}>
            <div className="flex items-center gap-2 px-4 py-2 rounded-full"
              style={{ background: 'rgba(59, 130, 246, 0.4)', backdropFilter: 'blur(10px)', border: '1px solid rgba(0, 229, 255, 0.5)' }}>
              <Maximize2 size={16} style={{ color: '#fff' }} />
              <span className="text-xs font-bold text-white uppercase tracking-wider">{t.expandHint}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Modal */}
      {open && (
        <div className="spectrogram-modal-backdrop" onClick={() => setOpen(false)}>
          <div className="relative" style={{ maxWidth: '95vw', maxHeight: '90vh' }} onClick={e => e.stopPropagation()}>
            <button
              id="spectrogram-close-btn"
              onClick={() => setOpen(false)}
              className="absolute -top-4 -right-4 w-9 h-9 rounded-full flex items-center justify-center z-10 transition-colors shadow-lg"
              style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-glow)', color: 'var(--text-secondary)' }}
            >
              <X size={18} />
            </button>
            <img
              src={base64}
              alt="Full Spectrogram"
              style={{ maxWidth: '90vw', maxHeight: '85vh', borderRadius: '14px', display: 'block' }}
            />
            {detectedCutoffHz && (
              <div className="absolute bottom-4 left-1/2 -translate-x-1/2 flex items-center gap-2 px-4 py-2 rounded-full shadow-xl"
                style={{ background: 'rgba(6, 8, 14, 0.85)', backdropFilter: 'blur(12px)', border: '1px solid rgba(0,229,255,0.4)' }}>
                <div className="w-3 h-0.5" style={{ background: 'var(--accent-cyan)', borderTop: '2px dashed var(--accent-cyan)' }} />
                <span className="text-sm font-semibold mono" style={{ color: 'var(--accent-cyan)' }}>
                  {t.detectedCutoffMark}: {(detectedCutoffHz / 1000).toFixed(2)} kHz
                </span>
              </div>
            )}
          </div>
        </div>
      )}
    </>
  );
}
