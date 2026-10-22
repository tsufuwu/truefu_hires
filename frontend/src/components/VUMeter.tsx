// components/VUMeter.tsx — Audiophile Analog VU Meter Component
import React from 'react';

export type VUTheme = 'tube' | 'sapphire';

interface Props {
  channelLabel: string;
  subLabel?: string;
  dbValue: number; // e.g. -20 to +3
  theme?: VUTheme;
  isPeak?: boolean;
}

// Map dB value (-20 to +3) to needle angle (-40 to +30 deg) using logarithmic response
function dbToAngle(db: number): number {
  if (db <= -20) return -40;
  if (db >= 3) return 32;

  // Key control points for authentic logarithmic VU scale
  const points = [
    { db: -20, angle: -40 },
    { db: -10, angle: -24 },
    { db: -7, angle: -15 },
    { db: -5, angle: -8 },
    { db: -3, angle: -1 },
    { db: -1, angle: 5 },
    { db: 0, angle: 9 }, // 0 dB line
    { db: 1, angle: 16 },
    { db: 2, angle: 23 },
    { db: 3, angle: 30 },
  ];

  for (let i = 0; i < points.length - 1; i++) {
    const p1 = points[i];
    const p2 = points[i + 1];
    if (db >= p1.db && db <= p2.db) {
      const ratio = (db - p1.db) / (p2.db - p1.db);
      return p1.angle + ratio * (p2.angle - p1.angle);
    }
  }
  return 0;
}

export const VUMeter: React.FC<Props> = ({
  channelLabel,
  subLabel = 'AUDIO SIGNAL LEVEL',
  dbValue,
  theme = 'tube',
  isPeak = false,
}) => {
  const angle = dbToAngle(dbValue);
  const isOverload = dbValue >= 0 || isPeak;

  const isAmber = theme === 'tube';

  // Colors based on theme
  const dialBg = isAmber
    ? 'linear-gradient(180deg, #241607 0%, #130b03 65%, #2a1805 100%)'
    : 'linear-gradient(180deg, #051d2d 0%, #03101c 65%, #072a40 100%)';

  const glowRgba = isAmber
    ? 'radial-gradient(ellipse 140px 90px at 50% 100%, rgba(245, 158, 11, 0.45) 0%, rgba(180, 83, 9, 0.15) 60%, transparent 100%)'
    : 'radial-gradient(ellipse 140px 90px at 50% 100%, rgba(0, 229, 255, 0.4) 0%, rgba(59, 130, 246, 0.15) 60%, transparent 100%)';

  const scaleColor = isAmber ? '#fbbf24' : '#38bdf8';
  const scaleSubColor = isAmber ? '#d97706' : '#0284c7';
  const textColor = isAmber ? '#fef3c7' : '#e0f2fe';

  // Scale markings coordinates on R = 82 from pivot (120, 122)
  const cx = 120;
  const cy = 122;
  const r = 82;

  const ticks = [
    { db: -20, label: '-20', angle: -40, isMajor: true },
    { db: -15, label: '', angle: -32, isMajor: false },
    { db: -10, label: '-10', angle: -24, isMajor: true },
    { db: -7, label: '-7', angle: -15, isMajor: true },
    { db: -5, label: '-5', angle: -8, isMajor: true },
    { db: -3, label: '-3', angle: -1, isMajor: true },
    { db: -2, label: '-2', angle: 2, isMajor: false },
    { db: -1, label: '-1', angle: 5, isMajor: false },
    { db: 0, label: '0', angle: 9, isMajor: true, isRed: true },
    { db: 1, label: '+1', angle: 16, isMajor: false, isRed: true },
    { db: 2, label: '+2', angle: 23, isMajor: false, isRed: true },
    { db: 3, label: '+3', angle: 30, isMajor: true, isRed: true },
  ];

  return (
    <div className="relative flex flex-col items-center select-none w-full max-w-[270px]">
      {/* Outer Chassis Bezel */}
      <div
        className="w-full relative rounded-xl p-[5px] transition-all duration-300"
        style={{
          background: 'linear-gradient(145deg, #2b3345 0%, #151a24 40%, #0d1117 100%)',
          boxShadow: 'inset 0 1px 1px rgba(255,255,255,0.18), 0 8px 24px -4px rgba(0,0,0,0.7), 0 0 0 1px rgba(0,0,0,0.8)',
        }}
      >
        {/* Inner Beveled Frame */}
        <div
          className="relative rounded-[9px] overflow-hidden"
          style={{
            background: dialBg,
            boxShadow: 'inset 0 3px 8px rgba(0,0,0,0.9), inset 0 0 0 1px rgba(255,255,255,0.06)',
            aspectRatio: '240 / 135',
          }}
        >
          {/* Internal Glow Bulb Emulation */}
          <div
            className="absolute inset-0 pointer-events-none"
            style={{ background: glowRgba }}
          />

          {/* SVG Dial Face */}
          <svg
            viewBox="0 0 240 135"
            className="w-full h-full relative z-10"
            xmlns="http://www.w3.org/2000/svg"
          >
            <defs>
              {/* Needle shadow filter */}
              <filter id={`needle-shadow-${channelLabel}`} x="-20%" y="-20%" width="140%" height="140%">
                <feDropShadow dx="1.5" dy="1.5" stdDeviation="1.5" floodColor="#000" floodOpacity="0.6" />
              </filter>

              {/* Hub Metallic Gradient */}
              <radialGradient id={`hub-grad-${channelLabel}`} cx="40%" cy="40%" r="60%">
                <stop offset="0%" stopColor="#e2e8f0" />
                <stop offset="45%" stopColor="#64748b" />
                <stop offset="85%" stopColor="#1e293b" />
                <stop offset="100%" stopColor="#0f172a" />
              </radialGradient>
            </defs>

            {/* Top Brand & Channel Header */}
            <text
              x="120"
              y="22"
              textAnchor="middle"
              fill={textColor}
              fontSize="8.5"
              fontFamily="sans-serif"
              fontWeight="800"
              letterSpacing="1.8"
              opacity="0.9"
            >
              VU METER
            </text>

            <text
              x="120"
              y="32"
              textAnchor="middle"
              fill={scaleSubColor}
              fontSize="6.5"
              fontFamily="sans-serif"
              fontWeight="600"
              letterSpacing="1.2"
              opacity="0.8"
            >
              {channelLabel}
            </text>

            {/* Normal Scale Arc (-20 to 0 dB) */}
            <path
              d="M 67.2 69.3 A 82 82 0 0 1 132.8 41.1"
              fill="none"
              stroke={scaleColor}
              strokeWidth="1.6"
              strokeLinecap="round"
              opacity="0.85"
            />

            {/* Overload Red Zone Arc (0 to +3 dB) */}
            <path
              d="M 132.8 41.1 A 82 82 0 0 1 161.0 51.0"
              fill="none"
              stroke="#f43f5e"
              strokeWidth="2.8"
              strokeLinecap="round"
              opacity="0.95"
            />

            {/* Tick Marks & Numbers */}
            {ticks.map((t, idx) => {
              const rad = (t.angle * Math.PI) / 180;
              const sin = Math.sin(rad);
              const cos = Math.cos(rad);
              const len = t.isMajor ? 6.5 : 3.5;
              const x1 = cx + (r - len) * sin;
              const y1 = cy - (r - len) * cos;
              const x2 = cx + r * sin;
              const y2 = cy - r * cos;

              // Text label coordinates (slightly inside tick)
              const textR = r - 12.5;
              const tx = cx + textR * sin;
              const ty = cy - textR * cos;

              const tickColor = t.isRed ? '#f43f5e' : scaleColor;

              return (
                <g key={idx}>
                  <line
                    x1={x1}
                    y1={y1}
                    x2={x2}
                    y2={y2}
                    stroke={tickColor}
                    strokeWidth={t.isMajor ? 1.5 : 1}
                    opacity={t.isMajor ? 0.95 : 0.6}
                  />
                  {t.isMajor && t.label && (
                    <text
                      x={tx}
                      y={ty + 2.5}
                      textAnchor="middle"
                      fill={t.isRed ? '#fb7185' : textColor}
                      fontSize="6.2"
                      fontFamily="'JetBrains Mono', monospace"
                      fontWeight="700"
                      opacity="0.95"
                    >
                      {t.label}
                    </text>
                  )}
                </g>
              );
            })}

            {/* Sub-scale label: dB and modulation */}
            <text
              x="62"
              y="58"
              fill={scaleSubColor}
              fontSize="5.5"
              fontFamily="'JetBrains Mono', monospace"
              fontWeight="600"
            >
              dB
            </text>

            <text
              x="120"
              y="114"
              textAnchor="middle"
              fill={textColor}
              fontSize="5.2"
              fontFamily="sans-serif"
              letterSpacing="0.8"
              opacity="0.65"
            >
              {subLabel}
            </text>

            {/* MECHANICAL NEEDLE (Pivot at 120, 122) */}
            <g
              filter={`url(#needle-shadow-${channelLabel})`}
              style={{
                transform: `rotate(${angle}deg)`,
                transformOrigin: '120px 122px',
                transition: 'transform 0.16s cubic-bezier(0.18, 0.89, 0.32, 1.25)',
              }}
            >
              {/* Needle Counterweight Tail */}
              <line
                x1="120"
                y1="122"
                x2="120"
                y2="132"
                stroke={isAmber ? '#78350f' : '#0369a1'}
                strokeWidth="2.5"
                strokeLinecap="round"
              />
              {/* Counterweight Disc */}
              <circle
                cx="120"
                cy="130"
                r="3"
                fill={isAmber ? '#92400e' : '#0284c7'}
              />

              {/* Needle Main Body */}
              <line
                x1="120"
                y1="122"
                x2="120"
                y2="46"
                stroke={isAmber ? '#1e293b' : '#f8fafc'}
                strokeWidth="1.4"
                strokeLinecap="round"
              />
              {/* Needle Crimson Tip */}
              <line
                x1="120"
                y1="54"
                x2="120"
                y2="42"
                stroke="#ef4444"
                strokeWidth="1.2"
                strokeLinecap="round"
              />
            </g>

            {/* Center Pivot Hub (Cap covering needle pivot) */}
            <circle
              cx="120"
              cy="122"
              r="7.5"
              fill={`url(#hub-grad-${channelLabel})`}
              stroke="#0f172a"
              strokeWidth="0.8"
            />
            <circle
              cx="120"
              cy="122"
              r="2.2"
              fill="#0f172a"
            />
            {/* Specular highlight on hub */}
            <circle
              cx="118.5"
              cy="120.5"
              r="1.2"
              fill="#ffffff"
              opacity="0.6"
            />
          </svg>

          {/* PEAK / OVERLOAD LED INDICATOR (Top Right) */}
          <div className="absolute top-2.5 right-3 z-20 flex items-center gap-1">
            <span
              className="text-[7.5px] font-bold tracking-wider"
              style={{
                color: isOverload ? '#f43f5e' : 'rgba(244, 63, 94, 0.4)',
                fontFamily: "'JetBrains Mono', monospace",
              }}
            >
              PEAK
            </span>
            <div
              className="w-2 h-2 rounded-full transition-all duration-100"
              style={{
                background: isOverload ? '#f43f5e' : '#450a0a',
                boxShadow: isOverload ? '0 0 8px #f43f5e, 0 0 14px rgba(244, 63, 94, 0.8)' : 'none',
                border: '1px solid rgba(0,0,0,0.6)',
              }}
            />
          </div>

          {/* Curved Glass Specular Highlight Overlay */}
          <div
            className="absolute inset-0 pointer-events-none z-30"
            style={{
              background:
                'linear-gradient(130deg, rgba(255,255,255,0.16) 0%, rgba(255,255,255,0.04) 40%, transparent 65%, rgba(255,255,255,0.02) 100%)',
              borderBottom: '1px solid rgba(255,255,255,0.06)',
            }}
          />
        </div>
      </div>
    </div>
  );
};
