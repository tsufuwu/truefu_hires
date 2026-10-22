// components/SignalMonitor.tsx — Compact Audiophile Hardware Signal Monitor
import { useEffect, useState } from 'react';
import { Sun, Moon, Radio } from 'lucide-react';
import { VUMeter, type VUTheme } from './VUMeter';

interface Props {
  isLoading: boolean;
  currentTarget?: string | null;
  lang?: 'vi' | 'en';
}

export function SignalMonitor({ isLoading, currentTarget, lang = 'vi' }: Props) {
  const [vuTheme, setVuTheme] = useState<VUTheme>('tube');
  const [leftDb, setLeftDb] = useState(-16);
  const [rightDb, setRightDb] = useState(-15);

  // Dynamic VU Meter needle ballistics
  useEffect(() => {
    let timer: number;

    if (isLoading) {
      // Dynamic bouncing during analysis
      timer = window.setInterval(() => {
        const base = -5 + Math.random() * 6;
        setLeftDb(Math.min(2.5, base + (Math.random() - 0.5) * 3));
        setRightDb(Math.min(2.5, base + (Math.random() - 0.5) * 3));
      }, 150);
    } else {
      // Gentle idle flutter
      timer = window.setInterval(() => {
        setLeftDb(-16 + (Math.random() - 0.5) * 2);
        setRightDb(-15.5 + (Math.random() - 0.5) * 2);
      }, 400);
    }

    return () => clearInterval(timer);
  }, [isLoading]);

  return (
    <div className="w-full max-w-2xl mx-auto select-none">
      <div
        className="rounded-2xl p-4 sm:p-5 transition-all"
        style={{
          background: 'linear-gradient(180deg, rgba(17, 24, 38, 0.85) 0%, rgba(11, 15, 23, 0.95) 100%)',
          border: '1px solid rgba(99, 130, 201, 0.16)',
          boxShadow: '0 8px 30px -8px rgba(0,0,0,0.6), inset 0 1px 0 rgba(255,255,255,0.06)',
          backdropFilter: 'blur(16px)',
        }}
      >
        {/* Top Monitor Bar */}
        <div className="flex items-center justify-between mb-3 px-1 pb-2 border-b border-slate-800/80">
          <div className="flex items-center gap-2">
            <Radio size={14} className="text-amber-400" />
            <span
              className="text-xs font-bold tracking-wider text-slate-300 uppercase"
              style={{ fontFamily: "'JetBrains Mono', monospace" }}
            >
              SIGNAL MONITOR // STEREO VU
            </span>
          </div>

          {/* Theme switcher for VU backlights */}
          <button
            onClick={() => setVuTheme(prev => (prev === 'tube' ? 'sapphire' : 'tube'))}
            className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[10px] font-bold tracking-wider uppercase transition-all"
            style={{
              background: vuTheme === 'tube' ? 'rgba(245, 158, 11, 0.12)' : 'rgba(2, 132, 199, 0.12)',
              border: vuTheme === 'tube' ? '1px solid rgba(245, 158, 11, 0.35)' : '1px solid rgba(2, 132, 199, 0.35)',
              color: vuTheme === 'tube' ? '#d97706' : '#0284c7',
            }}
          >
            {vuTheme === 'tube' ? <Sun size={11} /> : <Moon size={11} />}
            <span>{vuTheme === 'tube' ? (lang === 'vi' ? 'Đèn Tube (Amber)' : 'Tube Amber') : (lang === 'vi' ? 'Sapphire (Cyan)' : 'Sapphire Cyan')}</span>
          </button>
        </div>

        {/* Dual VU Meters */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-3 justify-items-center">
          <VUMeter
            channelLabel="CH-1 (LEFT)"
            subLabel={isLoading ? 'SCANNING SPECTRUM' : 'SIGNAL LEVEL L'}
            dbValue={leftDb}
            theme={vuTheme}
            isPeak={leftDb >= 0}
          />
          <VUMeter
            channelLabel="CH-2 (RIGHT)"
            subLabel={isLoading ? 'SCANNING SPECTRUM' : 'SIGNAL LEVEL R'}
            dbValue={rightDb}
            theme={vuTheme}
            isPeak={rightDb >= 0}
          />
        </div>

        {/* VFD Digital Readout Strip */}
        <div
          className="rounded-lg px-3 py-2 border flex flex-wrap items-center justify-between gap-2 text-[10.5px] font-bold"
          style={{
            background: 'linear-gradient(180deg, #02110c 0%, #031a12 50%, #010c08 100%)',
            borderColor: 'rgba(16, 185, 129, 0.3)',
            color: '#34d399',
            fontFamily: "'JetBrains Mono', monospace",
            textShadow: '0 0 6px rgba(16, 185, 129, 0.5)',
          }}
        >
          <div className="flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            <span>
              {isLoading
                ? `[DSP: ANALYZING ${currentTarget ? currentTarget.toUpperCase() : 'BITSTREAM'}]`
                : '[SYSTEM: 32-BIT BIT-PERFECT BITSTREAM]'}
            </span>
          </div>
          <div className="flex items-center gap-2 text-[9.5px] text-emerald-400/80">
            <span>CLOCK: 49.152MHz</span>
            <span>|</span>
            <span>STFT: 4096-BIN</span>
          </div>
        </div>
      </div>
    </div>
  );
}
