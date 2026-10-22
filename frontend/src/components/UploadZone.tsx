// components/UploadZone.tsx — Vibrant, Radiant & Styled Audio Upload Zone
import React, { useCallback, useRef, useState } from 'react';
import { Upload, Loader2, Sparkles, AudioWaveform, Music2 } from 'lucide-react';
import type { translations } from '../i18n';

interface Props {
  onFile: (file: File) => void;
  isLoading: boolean;
  t: typeof translations['en']['upload'];
}

const ACCEPTED_EXTENSIONS = [
  { ext: 'FLAC', color: '#00e5ff', glow: 'rgba(0, 229, 255, 0.6)' },
  { ext: 'WAV', color: '#38bdf8', glow: 'rgba(56, 189, 248, 0.6)' },
  { ext: 'ALAC', color: '#c084fc', glow: 'rgba(192, 132, 252, 0.6)' },
  { ext: 'APE', color: '#34d399', glow: 'rgba(52, 211, 153, 0.6)' },
  { ext: 'WV', color: '#818cf8', glow: 'rgba(129, 140, 248, 0.6)' },
  { ext: 'DSF', color: '#fbbf24', glow: 'rgba(251, 191, 36, 0.6)' },
  { ext: 'DFF', color: '#f43f5e', glow: 'rgba(244, 63, 94, 0.6)' },
];

const ACCEPT_STRING = '.flac,.wav,.alac,.ape,.wv,.dsf,.dff';

export function UploadZone({ onFile, isLoading, t }: Props) {
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFile = useCallback((file: File) => {
    if (isLoading) return;
    onFile(file);
  }, [onFile, isLoading]);

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  }, [handleFile]);

  const onDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setDragging(true);
  };

  const onDragLeave = () => setDragging(false);

  const onChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
    e.target.value = '';
  };

  return (
    <div className="w-full max-w-2xl mx-auto select-none">
      {/* Radiant Glowing Shimmer Border Wrapper */}
      <div className={`radiant-upload-wrapper ${dragging ? 'drag-active' : ''}`}>
        <div
          id="upload-zone"
          className={`radiant-upload-box relative flex flex-col items-center justify-center text-center p-8 sm:p-11 transition-all ${
            isLoading ? 'opacity-85 cursor-wait pointer-events-none' : ''
          }`}
          onDrop={onDrop}
          onDragOver={onDragOver}
          onDragLeave={onDragLeave}
          onClick={() => !isLoading && inputRef.current?.click()}
        >
          <input
            ref={inputRef}
            type="file"
            accept={ACCEPT_STRING}
            className="hidden"
            onChange={onChange}
            id="file-input"
          />

          {/* Ambient Inner Radiant Atmosphere */}
          <div
            className="absolute inset-0 pointer-events-none transition-opacity duration-500"
            style={{
              opacity: dragging ? 1 : 0.45,
              background: dragging
                ? 'radial-gradient(circle at 50% 45%, rgba(0, 229, 255, 0.25) 0%, rgba(168, 85, 247, 0.18) 45%, transparent 75%)'
                : 'radial-gradient(circle at 50% 45%, rgba(0, 229, 255, 0.1) 0%, rgba(59, 130, 246, 0.06) 50%, transparent 70%)',
            }}
          />

          {/* Central Vibrant Cluster */}
          <div className="relative mb-5 flex flex-col items-center">
            {/* Animated Equalizer Waveform Dance */}
            {!isLoading && (
              <div className="flex items-end justify-center gap-1.5 h-7 mb-3 px-3 py-1 rounded-full bg-slate-900/60 border border-cyan-500/20 backdrop-blur-md">
                {[10, 20, 14, 26, 18, 24, 12].map((height, i) => (
                  <div
                    key={i}
                    className="w-1 eq-bar"
                    style={{
                      height: `${height}px`,
                      background:
                        i % 2 === 0
                          ? 'linear-gradient(180deg, #00e5ff, #3b82f6)'
                          : 'linear-gradient(180deg, #a855f7, #ec4899)',
                      animationDelay: `${i * 0.16}s`,
                      boxShadow: '0 0 6px rgba(0, 229, 255, 0.5)',
                    }}
                  />
                ))}
              </div>
            )}

            {/* Glowing Icon Jewel */}
            {isLoading ? (
              <div
                className="w-18 h-18 rounded-2xl flex items-center justify-center shadow-lg relative"
                style={{
                  background: 'linear-gradient(135deg, rgba(0, 229, 255, 0.2), rgba(59, 130, 246, 0.3))',
                  border: '1.5px solid rgba(0, 229, 255, 0.6)',
                  boxShadow: '0 0 35px rgba(0, 229, 255, 0.5)',
                }}
              >
                <Loader2 size={34} className="spin-slow text-cyan-300" />
              </div>
            ) : (
              <div
                className="relative group transition-all duration-300 transform group-hover:scale-105"
                style={{
                  transform: dragging ? 'scale(1.08)' : 'none',
                }}
              >
                {/* Outer Neon Glow Ring */}
                <div
                  className="w-18 h-18 rounded-2xl flex items-center justify-center transition-all duration-300"
                  style={{
                    background: dragging
                      ? 'linear-gradient(135deg, rgba(0, 229, 255, 0.35) 0%, rgba(168, 85, 247, 0.45) 100%)'
                      : 'linear-gradient(135deg, rgba(20, 32, 54, 0.9) 0%, rgba(14, 22, 38, 0.95) 100%)',
                    border: dragging
                      ? '2px solid #00e5ff'
                      : '1.5px solid rgba(0, 229, 255, 0.35)',
                    boxShadow: dragging
                      ? '0 0 40px rgba(0, 229, 255, 0.6), inset 0 0 20px rgba(0, 229, 255, 0.3)'
                      : '0 10px 30px rgba(0, 0, 0, 0.6), 0 0 25px rgba(0, 229, 255, 0.18)',
                  }}
                >
                  <Upload
                    size={30}
                    className="transition-all duration-300"
                    style={{
                      color: dragging ? '#00e5ff' : '#93c5fd',
                      transform: dragging ? 'translateY(-3px)' : 'none',
                      filter: 'drop-shadow(0 0 10px rgba(0, 229, 255, 0.5))',
                    }}
                  />
                </div>

                {/* Sparkling Music Pill Accent */}
                <div
                  className="absolute -top-1.5 -right-1.5 w-7 h-7 rounded-full flex items-center justify-center shadow-lg"
                  style={{
                    background: 'linear-gradient(135deg, #00e5ff, #a855f7)',
                    boxShadow: '0 0 14px rgba(0, 229, 255, 0.7)',
                    border: '1.5px solid rgba(255, 255, 255, 0.4)',
                  }}
                >
                  <Music2 size={13} className="text-slate-950 stroke-[2.5]" />
                </div>
              </div>
            )}
          </div>

          {/* Primary Action Texts */}
          <div className="relative z-10 max-w-md mx-auto mb-5">
            {isLoading ? (
              <div className="flex flex-col items-center gap-2">
                <div className="flex items-center gap-2 text-lg font-bold text-cyan-300">
                  <Sparkles size={18} className="text-cyan-400" />
                  <span>{t.analyzingTitle}</span>
                </div>
                <p className="text-xs sm:text-sm text-slate-400 leading-relaxed max-w-sm">
                  {t.analyzingDesc}
                </p>
                <div className="w-60 h-2 rounded-full overflow-hidden mt-3 bg-slate-900 border border-cyan-500/30 shadow-[0_0_15px_rgba(0,229,255,0.25)]">
                  <div className="progress-bar h-full w-full" />
                </div>
              </div>
            ) : (
              <div className="flex flex-col items-center gap-1.5">
                <h3 className="text-xl sm:text-2xl font-extrabold tracking-tight text-slate-100">
                  {t.title}
                </h3>
                <p className="text-xs sm:text-sm text-slate-400">
                  {t.browseText}{' '}
                  <span className="font-bold text-cyan-400 underline underline-offset-4 decoration-cyan-400/50 hover:text-cyan-300 hover:decoration-cyan-300 transition-colors">
                    {t.browseLink}
                  </span>
                </p>
              </div>
            )}
          </div>

          {/* Radiant Format Chips */}
          {!isLoading && (
            <div className="relative z-10 flex flex-wrap items-center justify-center gap-2 max-w-lg mx-auto mb-4">
              {ACCEPTED_EXTENSIONS.map(({ ext, color, glow }) => (
                <div
                  key={ext}
                  className="px-3 py-1 rounded-xl text-[11px] font-bold tracking-wider transition-all duration-200 hover:-translate-y-0.5"
                  style={{
                    background: 'linear-gradient(180deg, rgba(255, 255, 255, 0.06) 0%, rgba(255, 255, 255, 0.02) 100%)',
                    border: '1px solid rgba(255, 255, 255, 0.1)',
                    boxShadow: '0 4px 12px rgba(0, 0, 0, 0.4)',
                    color: 'rgba(241, 245, 249, 0.9)',
                  }}
                >
                  <span
                    className="w-1.5 h-1.5 rounded-full inline-block mr-1.5"
                    style={{ background: color, boxShadow: `0 0 7px ${glow}` }}
                  />
                  .{ext}
                </div>
              ))}
            </div>
          )}

          {/* Bottom Micro-Info */}
          {!isLoading && (
            <div className="relative z-10 pt-3.5 border-t border-slate-800/80 flex flex-wrap items-center justify-between w-full max-w-md text-[11px] text-slate-400 gap-2">
              <span className="flex items-center gap-1.5">
                <AudioWaveform size={13} className="text-cyan-400" />
                {t.samplingInfo}
              </span>
              <span className="text-slate-500">{t.fileLimits}</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
