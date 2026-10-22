// components/TransportDeck.tsx — Audiophile Reference Master Transport & Console Deck
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Disc3, Loader2, Sparkles, AudioWaveform, Zap, Sun, Moon } from 'lucide-react';
import { VUMeter, type VUTheme } from './VUMeter';
import type { translations } from '../i18n';

interface Props {
  onFile: (file: File) => void;
  isLoading: boolean;
  currentTarget?: string | null;
  t: typeof translations['en']['upload'];
  lang?: 'vi' | 'en';
}

const ACCEPTED_EXTENSIONS = [
  { ext: 'FLAC', color: '#00e5ff', badge: 'LOSSLESS' },
  { ext: 'WAV', color: '#38bdf8', badge: 'PCM RAW' },
  { ext: 'ALAC', color: '#a855f7', badge: 'APPLE M4A' },
  { ext: 'APE', color: '#10b981', badge: 'MONKEY' },
  { ext: 'WV', color: '#818cf8', badge: 'WAVPACK' },
  { ext: 'DSF', color: '#f59e0b', badge: 'DSD 1-BIT' },
  { ext: 'DFF', color: '#ec4899', badge: 'DSD STREAM' },
];

const ACCEPT_STRING = '.flac,.wav,.alac,.ape,.wv,.dsf,.dff';

export function TransportDeck({ onFile, isLoading, currentTarget, t, lang = 'vi' }: Props) {
  const [dragging, setDragging] = useState(false);
  const [vuTheme, setVuTheme] = useState<VUTheme>('tube');
  const [leftDb, setLeftDb] = useState(-16);
  const [rightDb, setRightDb] = useState(-15);
  const inputRef = useRef<HTMLInputElement>(null);

  // Dynamic VU Meter needle ballistics & idle breathing
  useEffect(() => {
    let timer: number;

    if (isLoading) {
      // During DSP analysis: needles bounce vigorously to simulate live frequency scanning
      timer = window.setInterval(() => {
        const base = -4 + Math.random() * 6; // -4 to +2 dB
        setLeftDb(Math.min(2.5, base + (Math.random() - 0.5) * 3));
        setRightDb(Math.min(2.5, base + (Math.random() - 0.5) * 3));
      }, 140);
    } else if (dragging) {
      // While dragging file over: needles jump to peak level
      setLeftDb(0.5);
      setRightDb(1.2);
    } else {
      // Idle state: organic micro-flutter (thermal floor noise -17 to -13 dB)
      timer = window.setInterval(() => {
        setLeftDb(-16 + (Math.random() - 0.5) * 2.5);
        setRightDb(-15.5 + (Math.random() - 0.5) * 2.5);
      }, 350);
    }

    return () => clearInterval(timer);
  }, [isLoading, dragging]);

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

  const toggleTheme = (e: React.MouseEvent) => {
    e.stopPropagation();
    setVuTheme(prev => (prev === 'tube' ? 'sapphire' : 'tube'));
  };

  return (
    <div className="w-full max-w-4xl mx-auto select-none">
      {/* ── HIGH-END HARDWARE MASTER CHASSIS FACEPLATE ── */}
      <div
        className="relative rounded-[28px] p-6 sm:p-8 transition-all duration-300"
        style={{
          background: 'linear-gradient(180deg, #161b26 0%, #0d121c 45%, #080c14 100%)',
          border: '1px solid rgba(255, 255, 255, 0.1)',
          boxShadow:
            '0 25px 60px -15px rgba(0, 0, 0, 0.85), inset 0 1px 0 rgba(255, 255, 255, 0.18), inset 0 -1px 0 rgba(0, 0, 0, 0.8), 0 0 0 1px rgba(0, 0, 0, 0.9)',
        }}
      >
        {/* 4 Corner Machined Hex Screws */}
        <div className="absolute top-3.5 left-4 chassis-screw" title="Machined Torx Fastener" />
        <div className="absolute top-3.5 right-4 chassis-screw" title="Machined Torx Fastener" />
        <div className="absolute bottom-3.5 left-4 chassis-screw" title="Machined Torx Fastener" />
        <div className="absolute bottom-3.5 right-4 chassis-screw" title="Machined Torx Fastener" />

        {/* Chassis Top Branding & Status Strip */}
        <div className="flex flex-wrap items-center justify-between gap-3 mb-6 pb-3 border-b border-slate-800/80 px-2">
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-sm bg-gradient-to-br from-amber-400 to-amber-600 shadow-[0_0_8px_rgba(245,158,11,0.6)]" />
              <span
                className="text-xs sm:text-sm font-extrabold tracking-widest text-slate-200"
                style={{ fontFamily: "'JetBrains Mono', monospace" }}
              >
                TRUEFU HIRES TF-2000 PRO
              </span>
            </div>
            <span className="hidden sm:inline-block text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded bg-slate-800/80 text-amber-400/90 border border-amber-500/20">
              REFERENCE AUDIO MASTERING LAB
            </span>
          </div>

          {/* Right Controls: Backlight Switcher */}
          <div className="flex items-center gap-2">
            <button
              onClick={toggleTheme}
              className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[10px] font-bold tracking-wider uppercase transition-all"
              style={{
                background: vuTheme === 'tube' ? 'rgba(245, 158, 11, 0.15)' : 'rgba(0, 229, 255, 0.15)',
                border: vuTheme === 'tube' ? '1px solid rgba(245, 158, 11, 0.4)' : '1px solid rgba(0, 229, 255, 0.4)',
                color: vuTheme === 'tube' ? '#fbbf24' : '#38bdf8',
              }}
              title={lang === 'vi' ? 'Đổi đèn nền VU (Bóng đèn vàng / Sapphire xanh)' : 'Switch VU Backlight (Warm Tube / Sapphire Cyan)'}
            >
              {vuTheme === 'tube' ? <Sun size={11} /> : <Moon size={11} />}
              <span>{vuTheme === 'tube' ? (lang === 'vi' ? 'Đèn Tube (Amber)' : 'Tube Amber') : (lang === 'vi' ? 'Sapphire (Cyan)' : 'Sapphire Cyan')}</span>
            </button>
          </div>
        </div>

        {/* ── DUAL STEREO ANALOG VU METERS ── */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6 px-1 justify-items-center">
          <VUMeter
            channelLabel="CH-1 (LEFT)"
            subLabel={isLoading ? 'SCANNING LEFT SPECTRUM' : 'SIGNAL LEVEL L'}
            dbValue={leftDb}
            theme={vuTheme}
            isPeak={leftDb >= 0}
          />
          <VUMeter
            channelLabel="CH-2 (RIGHT)"
            subLabel={isLoading ? 'SCANNING RIGHT SPECTRUM' : 'SIGNAL LEVEL R'}
            dbValue={rightDb}
            theme={vuTheme}
            isPeak={rightDb >= 0}
          />
        </div>

        {/* ── VACUUM FLUORESCENT DISPLAY (VFD) SCREEN STRIP ── */}
        <div
          className="mb-6 rounded-xl p-3 border overflow-hidden relative"
          style={{
            background: 'linear-gradient(180deg, #02110c 0%, #031a12 50%, #010c08 100%)',
            borderColor: 'rgba(16, 185, 129, 0.3)',
            boxShadow: 'inset 0 2px 10px rgba(0,0,0,0.9), 0 0 15px rgba(16, 185, 129, 0.08)',
          }}
        >
          {/* Subtle Scanlines Overlay */}
          <div className="absolute inset-0 pointer-events-none vfd-scanlines" />

          <div
            className="flex flex-wrap items-center justify-between gap-2 text-[11px] font-bold text-emerald-400 relative z-10"
            style={{ fontFamily: "'JetBrains Mono', monospace", textShadow: '0 0 6px rgba(16, 185, 129, 0.7)' }}
          >
            <div className="flex items-center gap-2">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
              <span>
                {isLoading
                  ? `[DSP ENGINE: ANALYZING ${currentTarget ? currentTarget.toUpperCase() : 'PCM BITSTREAM'}]`
                  : dragging
                  ? '[CARRIER DETECTED: DROP TO ENGAGE OPTICAL PICKUP]'
                  : '[SYSTEM: 32-BIT BIT-PERFECT BITSTREAM CORE]'}
              </span>
            </div>
            <div className="flex items-center gap-3 text-emerald-500/80 text-[10px]">
              <span>CLOCK: 49.152MHz FEMTO</span>
              <span className="hidden sm:inline">|</span>
              <span className="hidden sm:inline">STFT: 4096-BIN FFT</span>
              <span className="hidden sm:inline">|</span>
              <span className="text-emerald-300 font-extrabold">STATUS: {isLoading ? 'PROCESSING' : 'STANDBY'}</span>
            </div>
          </div>
        </div>

        {/* ── TOP-LOADING OPTICAL MASTER TRANSPORT BAY (DROP TARGET) ── */}
        <div
          id="upload-zone"
          className={`transport-bay relative flex flex-col items-center justify-center p-8 sm:p-12 rounded-2xl cursor-pointer transition-all duration-300 overflow-hidden ${
            dragging ? 'transport-bay-active' : ''
          } ${isLoading ? 'cursor-wait pointer-events-none' : ''}`}
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

          {/* Concentric Turntable / Optical CD Grooves Backdrop */}
          <div
            className={`absolute w-[340px] h-[340px] sm:w-[420px] sm:h-[420px] rounded-full pointer-events-none transition-transform duration-700 ${
              isLoading ? 'spin-turntable' : dragging ? 'scale-105' : 'hover:scale-102'
            }`}
            style={{
              background: `
                radial-gradient(circle at center, transparent 35px, #0e1420 36px, #161e2e 38px, transparent 39px),
                radial-gradient(circle at center, transparent 65px, #1e283b 66px, #0f172a 68px, transparent 69px),
                radial-gradient(circle at center, transparent 95px, #1e293b 96px, #0f172a 98px, transparent 99px),
                radial-gradient(circle at center, transparent 125px, #1e293b 126px, #0f172a 128px, transparent 129px),
                radial-gradient(circle at center, transparent 155px, #1e293b 156px, #0f172a 158px, transparent 159px),
                radial-gradient(circle at center, transparent 185px, #1e293b 186px, #0f172a 188px, transparent 189px),
                conic-gradient(from 0deg, rgba(0, 229, 255, 0.08), rgba(245, 158, 11, 0.06), rgba(168, 85, 247, 0.08), rgba(0, 229, 255, 0.08))
              `,
              border: dragging
                ? '2px solid rgba(0, 229, 255, 0.6)'
                : '2px solid rgba(255, 255, 255, 0.08)',
              boxShadow: dragging
                ? '0 0 50px rgba(0, 229, 255, 0.35), inset 0 0 40px rgba(0, 229, 255, 0.2)'
                : 'inset 0 0 35px rgba(0, 0, 0, 0.8), 0 10px 30px rgba(0, 0, 0, 0.6)',
            }}
          />

          {/* Strobe Rim Optical Dots (Turntable rim illusion) */}
          <div
            className={`absolute w-[330px] h-[330px] sm:w-[410px] sm:h-[410px] rounded-full pointer-events-none strobe-ring ${
              isLoading ? 'spin-turntable-reverse' : ''
            }`}
          />

          {/* Laser Scanning Pickup Beam across radius */}
          <div
            className="absolute inset-0 pointer-events-none transition-opacity duration-300"
            style={{
              opacity: dragging || isLoading ? 1 : 0.15,
              background:
                'radial-gradient(circle at 50% 50%, rgba(0, 229, 255, 0.15) 0%, transparent 60%)',
            }}
          />

          {/* Center Spindle & Heavy Stabilizer Puck / Clamp */}
          <div className="relative z-10 mb-5 flex flex-col items-center">
            {isLoading ? (
              <div
                className="relative w-24 h-24 rounded-full flex items-center justify-center"
                style={{
                  background: 'linear-gradient(145deg, #1e293b, #0f172a)',
                  border: '2px solid rgba(0, 229, 255, 0.6)',
                  boxShadow: '0 0 30px rgba(0, 229, 255, 0.4), inset 0 2px 4px rgba(255,255,255,0.2)',
                }}
              >
                <Loader2 size={40} className="spin-slow" style={{ color: 'var(--accent-cyan)' }} />
                <div className="absolute w-4 h-4 rounded-full bg-cyan-400 shadow-[0_0_12px_#00e5ff]" />
              </div>
            ) : (
              <div
                className="relative group-hover:scale-105 transition-all duration-300 w-24 h-24 rounded-full flex items-center justify-center"
                style={{
                  background: dragging
                    ? 'linear-gradient(145deg, #0284c7 0%, #0369a1 40%, #0c4a6e 100%)'
                    : 'linear-gradient(145deg, #334155 0%, #1e293b 50%, #0f172a 100%)',
                  border: dragging
                    ? '2px solid #00e5ff'
                    : '2px solid rgba(245, 158, 11, 0.4)',
                  boxShadow: dragging
                    ? '0 0 35px rgba(0, 229, 255, 0.6), inset 0 2px 5px rgba(255,255,255,0.4)'
                    : '0 8px 25px rgba(0, 0, 0, 0.7), inset 0 2px 4px rgba(255,255,255,0.2), inset 0 -2px 4px rgba(0,0,0,0.8)',
                }}
              >
                {/* Brass Gold Ring on Disc Stabilizer */}
                <div
                  className="absolute inset-1.5 rounded-full pointer-events-none"
                  style={{
                    border: '1.5px solid rgba(245, 158, 11, 0.5)',
                  }}
                />

                {/* Laser Jewel Diode in Center */}
                <div
                  className="w-10 h-10 rounded-full flex items-center justify-center transition-all duration-200"
                  style={{
                    background: dragging ? '#00e5ff' : '#0f172a',
                    border: '1.5px solid rgba(255, 255, 255, 0.3)',
                    boxShadow: dragging ? '0 0 20px #00e5ff' : 'inset 0 2px 4px rgba(0,0,0,0.9)',
                  }}
                >
                  {dragging ? (
                    <Zap size={18} className="text-slate-950 animate-bounce" />
                  ) : (
                    <Disc3 size={20} className="text-amber-400 group-hover:rotate-45 transition-transform" />
                  )}
                </div>
              </div>
            )}
          </div>

          {/* Main Action Callout */}
          <div className="relative z-10 max-w-lg text-center mb-5">
            {isLoading ? (
              <div className="flex flex-col items-center gap-2">
                <div className="flex items-center gap-2 text-lg font-bold text-cyan-400">
                  <Sparkles size={18} />
                  <span>{t.analyzingTitle}</span>
                </div>
                <p className="text-xs sm:text-sm text-slate-400 max-w-md">
                  {t.analyzingDesc}
                </p>
                {/* Audio Progress Meter */}
                <div className="w-64 h-2 rounded-full overflow-hidden mt-3 p-0.5 bg-slate-900 border border-cyan-500/30">
                  <div className="progress-bar h-full w-full rounded-full" />
                </div>
              </div>
            ) : (
              <div className="flex flex-col items-center gap-1.5">
                <div className="inline-flex items-center gap-1.5 text-[11px] font-extrabold uppercase tracking-widest text-amber-400/90 mb-1">
                  <Zap size={12} className="text-amber-400" />
                  <span>{lang === 'vi' ? 'KHAY ĐĨA MASTER TRANSPORT' : 'MASTER TRANSPORT OPTICAL BAY'}</span>
                </div>
                <h3 className="text-xl sm:text-2xl font-black tracking-tight text-slate-100">
                  {t.title}
                </h3>
                <p className="text-xs sm:text-sm text-slate-400">
                  {t.browseText}{' '}
                  <span className="font-bold text-cyan-400 underline underline-offset-4 hover:text-cyan-300">
                    {t.browseLink}
                  </span>
                </p>
              </div>
            )}
          </div>

          {/* Gold-plated Audio Format Cartridges */}
          {!isLoading && (
            <div className="relative z-10 flex flex-wrap items-center justify-center gap-2 max-w-xl mx-auto mb-4">
              {ACCEPTED_EXTENSIONS.map(({ ext, color, badge }) => (
                <div
                  key={ext}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg transition-transform hover:-translate-y-0.5"
                  style={{
                    background: 'linear-gradient(180deg, #1e293b 0%, #0f172a 100%)',
                    border: '1px solid rgba(255, 255, 255, 0.1)',
                    boxShadow: '0 2px 6px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.1)',
                  }}
                >
                  <span
                    className="w-2 h-2 rounded-full shrink-0"
                    style={{ background: color, boxShadow: `0 0 6px ${color}` }}
                  />
                  <span className="text-xs font-black tracking-wider text-slate-200">
                    .{ext}
                  </span>
                  <span className="text-[9px] font-bold text-slate-500 tracking-tight">
                    {badge}
                  </span>
                </div>
              ))}
            </div>
          )}

          {/* Bottom Technical Spec Footer */}
          {!isLoading && (
            <div className="relative z-10 pt-3 border-t border-slate-800/80 flex flex-wrap items-center justify-between w-full max-w-lg text-[10.5px] text-slate-400">
              <span className="flex items-center gap-1.5">
                <AudioWaveform size={13} className="text-cyan-400" />
                {t.samplingInfo}
              </span>
              <span className="text-slate-500">{t.fileLimits}</span>
            </div>
          )}
        </div>

        {/* Chassis Lower Engraving & Laboratory Certification */}
        <div className="mt-5 pt-3 border-t border-slate-800/60 flex flex-wrap items-center justify-between text-[10px] text-slate-500 uppercase tracking-widest px-2 font-mono">
          <span>CLASS-A DISCRETE DSP · TRUE 32-BIT FLOAT CORE</span>
          <span>ACCURATERIP / AES-17 COMPLIANT VERIFICATION</span>
        </div>
      </div>
    </div>
  );
}
