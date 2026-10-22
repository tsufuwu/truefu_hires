import { useState } from 'react';
import { createPortal } from 'react-dom';
import { ShieldCheck, ShieldAlert, ShieldX, AlertTriangle, CheckCircle2, XCircle, Maximize2, X, Disc3 } from 'lucide-react';
import type { VerdictData, MetadataData } from '../api';
import type { translations, Language } from '../i18n';
import { localizeVerdictSummary } from '../utils/localize';
import { MiniAudioPlayer } from './MiniAudioPlayer';

interface Props {
  verdict: VerdictData;
  metadata: MetadataData;
  filename: string;
  t: typeof translations['en']['verdict'];
  lang?: Language;
  audioUrl?: string | null;
}

function getVerdictStyle(status: string, score: number) {
  if (status === 'AUTHENTIC_LOSSLESS' || score >= 85) {
    return { cls: 'verdict-authentic', gaugeColor: 'var(--accent-green)', Icon: ShieldCheck, BadgeIcon: CheckCircle2 };
  }
  if (score >= 60 || status.startsWith('SUSPICIOUS')) {
    return { cls: 'verdict-suspicious', gaugeColor: 'var(--accent-amber)', Icon: ShieldAlert, BadgeIcon: AlertTriangle };
  }
  return { cls: 'verdict-fake', gaugeColor: 'var(--accent-red)', Icon: ShieldX, BadgeIcon: XCircle };
}

function ScoreGauge({ score, color }: { score: number; color: string }) {
  const R = 52;
  const circ = 2 * Math.PI * R;
  const clampedScore = Math.max(0, Math.min(100, score));
  const dash = (clampedScore / 100) * circ;

  return (
    <svg width="130" height="130" viewBox="0 0 130 130" className="relative" style={{ filter: `drop-shadow(0 0 12px ${color}40)` }}>
      {/* Track */}
      <circle cx="65" cy="65" r={R} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="8" />
      {/* Progress */}
      <circle
        cx="65" cy="65" r={R}
        fill="none"
        stroke={color}
        strokeWidth="8"
        strokeLinecap="round"
        strokeDasharray={clampedScore >= 100 ? `${circ}` : `${dash} ${circ}`}
        strokeDashoffset={0}
        transform="rotate(-90 65 65)"
        style={{ transition: 'stroke-dasharray 1s ease' }}
      />
      {/* Score text */}
      <text x="65" y="62" textAnchor="middle" dominantBaseline="middle"
        style={{ fill: color, fontSize: '24px', fontWeight: 700, fontFamily: 'JetBrains Mono, monospace' }}>
        {score}
      </text>
      <text x="65" y="81" textAnchor="middle" dominantBaseline="middle"
        style={{ fill: 'rgba(255,255,255,0.35)', fontSize: '10px', fontFamily: 'Inter, sans-serif', letterSpacing: '0.1em' }}>
        /100
      </text>
    </svg>
  );
}

function fmt(sr: number) {
  if (sr >= 1000) return `${(sr / 1000).toFixed(sr % 1000 === 0 ? 0 : 1)} kHz`;
  return `${sr} Hz`;
}

export function VerdictBanner({ verdict, metadata, filename, t, lang = 'vi', audioUrl }: Props) {
  const [showCoverModal, setShowCoverModal] = useState(false);
  const { cls, gaugeColor, Icon } = getVerdictStyle(verdict.status, verdict.score);

  const localizedStatusLabel =
    (t.statusLabels as Record<string, string>)[verdict.status] || verdict.label;

  const localizedConfidence =
    (t.confidenceLevels as Record<string, string>)[verdict.confidence] || verdict.confidence;

  const confidenceDot = verdict.confidence === 'HIGH'
    ? 'var(--accent-green)'
    : verdict.confidence === 'MEDIUM' ? 'var(--accent-amber)' : 'var(--accent-red)';

  const channelsDisplay =
    metadata.channels === 2
      ? t.metaLabels.stereo
      : metadata.channels === 1
      ? t.metaLabels.mono
      : `${metadata.channels} ${t.metaLabels.ch}`;

  const localizedSummary = localizeVerdictSummary(verdict, lang);
  const isAuthentic = verdict.score >= 85;
  const isSuspicious = verdict.score >= 60 && verdict.score < 85;

  return (
    <>
      <div className={`card card-glow fade-in p-5 sm:p-7 ${cls}`} id="verdict-banner">
        <div className="flex flex-col lg:flex-row items-center lg:items-start gap-6 sm:gap-8">
          {/* Left Visuals: [Cover Art + Mini Player right below it] and [Score Gauge] */}
          <div className="flex flex-row items-center lg:items-start gap-4 sm:gap-6 shrink-0 justify-center">
            {/* Column 1: Album Cover Art + Mini Media Player */}
            <div className="flex flex-col items-center gap-2 shrink-0">
              {metadata.cover_art_base64 ? (
                <div
                  onClick={() => setShowCoverModal(true)}
                  className="relative group cursor-pointer shrink-0 transition-transform duration-300 hover:scale-105"
                  title={lang === 'vi' ? 'Nhấp để xem ảnh bìa kích thước đầy đủ' : 'Click to view full cover art'}
                >
                  <div className="w-[125px] h-[125px] sm:w-[140px] sm:h-[140px] rounded-2xl overflow-hidden border border-white/20 shadow-2xl relative bg-slate-900/90 group-hover:border-cyan-400/70 group-hover:shadow-[0_0_25px_rgba(34,211,238,0.35)] transition-all duration-300">
                    <img
                      src={metadata.cover_art_base64}
                      alt={metadata.title || filename}
                      className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-110"
                    />
                    <div className="absolute inset-0 bg-gradient-to-tr from-black/40 via-transparent to-white/20 pointer-events-none" />
                    <div className="absolute bottom-1.5 right-1.5 bg-black/75 backdrop-blur-md rounded-md p-1 opacity-0 group-hover:opacity-100 transition-opacity duration-200 border border-white/10">
                      <Maximize2 size={13} className="text-cyan-300" />
                    </div>
                  </div>
                </div>
              ) : (
                <div className="w-[125px] h-[125px] sm:w-[140px] sm:h-[140px] rounded-2xl flex flex-col items-center justify-center border border-white/15 bg-slate-900/90 shadow-xl relative">
                  <Disc3 size={44} className="text-cyan-400/60" />
                  <span className="text-[11px] text-slate-400 mt-2 font-mono uppercase font-bold tracking-wider">{metadata.codec}</span>
                </div>
              )}

              {/* Mini Audio Player right below the cover art */}
              {audioUrl && (
                <MiniAudioPlayer
                  audioUrl={audioUrl}
                  durationSec={metadata.duration_sec}
                  isDsd={metadata.is_dsd}
                  lang={lang}
                />
              )}
            </div>

            {/* Column 2: Score gauge */}
            <div className="shrink-0 pt-1">
              <ScoreGauge score={verdict.score} color={gaugeColor} />
            </div>
          </div>

          {/* Main Content Area */}
          <div className="flex-1 min-w-0 w-full text-center sm:text-left flex flex-col justify-center">
            {/* Optional Track Title & Artist if available from tags */}
            {(metadata.title || metadata.artist) && (
              <div className="flex items-center gap-2.5 mb-2.5 flex-wrap justify-center sm:justify-start">
                {metadata.title && (
                  <span className="text-xl sm:text-2xl lg:text-3xl font-extrabold text-white tracking-tight drop-shadow-sm">
                    {metadata.title}
                  </span>
                )}
                {metadata.artist && (
                  <span className="text-xs sm:text-sm font-bold text-cyan-300 bg-cyan-950/70 px-3 py-1 rounded-full border border-cyan-500/35">
                    {metadata.artist}
                  </span>
                )}
                {metadata.album && (
                  <span className="text-xs sm:text-sm text-slate-400 italic">
                    ({metadata.album})
                  </span>
                )}
              </div>
            )}

            <div className="flex items-center gap-3 mb-2.5 flex-wrap justify-center sm:justify-start">
              <Icon
                size={26}
                className={
                  isAuthentic
                    ? 'text-emerald-400'
                    : isSuspicious
                    ? 'text-amber-400'
                    : 'text-rose-400'
                }
              />
              <h2 className="text-2xl sm:text-3xl font-extrabold tracking-tight truncate text-white">
                {localizedStatusLabel}
              </h2>
              <span className="flex items-center gap-1.5 text-xs sm:text-sm font-semibold px-3 py-1 rounded-full"
                style={{ background: 'rgba(0,0,0,0.35)', border: '1px solid rgba(255,255,255,0.12)', color: 'var(--text-secondary)' }}>
                <span className="pulse-dot w-2 h-2 rounded-full inline-block" style={{ background: confidenceDot }} />
                <span>
                  {lang === 'vi'
                    ? `${t.confidence} ${localizedConfidence.toLowerCase()}`
                    : `${localizedConfidence} ${t.confidence}`}
                </span>
              </span>
            </div>

            {/* Highlighted Box for Issues / Anomaly Advisory, or Clean Summary for Authentic */}
            {isAuthentic ? (
              <p className="text-sm sm:text-base leading-relaxed mb-4 text-emerald-200 text-center sm:text-left font-medium">
                {localizedSummary}
              </p>
            ) : isSuspicious ? (
              <div className="p-3.5 sm:p-4 mb-4 rounded-xl border border-amber-500/50 bg-amber-950/40 text-amber-200 text-xs sm:text-sm leading-relaxed flex items-start gap-3 shadow-[0_0_15px_rgba(245,158,11,0.15)]">
                <ShieldAlert size={22} className="text-amber-400 shrink-0 mt-0.5" />
                <div className="flex-1 text-left">
                  <span className="font-bold text-amber-300 block mb-1 uppercase tracking-wide text-xs sm:text-sm">
                    {lang === 'vi' ? '⚠️ Phát hiện đặc điểm bất thường / Cần xem xét:' : '⚠️ Anomalies Detected / Review Recommended:'}
                  </span>
                  <span className="leading-relaxed font-medium block mb-2 text-xs sm:text-sm">
                    {localizedSummary.replace(/^Phát hiện bất thường:\s*/i, '').replace(/^Issues detected:\s*/i, '')}
                  </span>
                  <span className="text-xs block text-amber-300/85 italic border-t border-amber-500/25 pt-1.5 mt-1.5">
                    💡 {lang === 'vi'
                      ? 'Lời khuyên: Phát hiện đặc điểm cấu trúc tần số lạ, có thể do bản phối (Mastering quirk) hoặc file nén nhẹ. Cần nghe thử hoặc đối chiếu thêm.'
                      : 'Advisory: Unusual frequency characteristic detected. Could be a mastering quirk or mild compression. Critical listening or cross-reference recommended.'}
                  </span>
                </div>
              </div>
            ) : (
              <div className="p-3.5 sm:p-4 mb-4 rounded-xl border-2 border-rose-500/50 bg-rose-950/40 text-rose-200 text-xs sm:text-sm leading-relaxed flex items-start gap-3 shadow-[0_0_15px_rgba(244,63,94,0.15)]">
                <ShieldX size={22} className="text-rose-400 shrink-0 mt-0.5" />
                <div className="flex-1 text-left">
                  <span className="font-bold text-rose-300 block mb-1 uppercase tracking-wide text-xs sm:text-sm">
                    {lang === 'vi' ? '🚫 Phát hiện bất thường / Không đạt chuẩn:' : '🚫 Critical Anomalies / Non-Compliant:'}
                  </span>
                  <span className="leading-relaxed font-medium text-xs sm:text-sm">
                    {localizedSummary.replace(/^Phát hiện bất thường:\s*/i, '').replace(/^Issues detected:\s*/i, '')}
                  </span>
                </div>
              </div>
            )}

            {/* Metadata chips */}
            <div className="flex flex-wrap gap-2.5 sm:gap-3 justify-center sm:justify-start">
              {[
                { label: t.metaLabels.file, value: filename },
                { label: t.metaLabels.codec, value: metadata.codec },
                { label: t.metaLabels.sampleRate, value: fmt(metadata.sample_rate_hz) },
                { label: t.metaLabels.channels, value: channelsDisplay },
                { label: t.metaLabels.duration, value: `${Math.floor(metadata.duration_sec / 60)}:${String(Math.round(metadata.duration_sec % 60)).padStart(2, '0')}` },
                ...(metadata.bitrate_kbps ? [{ label: t.metaLabels.bitrate, value: `${metadata.bitrate_kbps} kbps` }] : []),
                ...(metadata.is_dsd ? [{ label: t.metaLabels.dsd, value: t.metaLabels.yes }] : []),
              ].map(({ label, value }) => (
                <div key={label} className="flex flex-col"
                  style={{ background: 'rgba(0,0,0,0.35)', borderRadius: '12px', padding: '7px 14px', border: '1px solid rgba(255,255,255,0.08)' }}>
                  <span className="text-[10px] sm:text-[11px] uppercase tracking-wider font-semibold text-slate-400">{label}</span>
                  <span className="text-sm sm:text-base font-bold mono text-slate-100">{value}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Album Cover Art Lightbox Modal */}
      {showCoverModal && metadata.cover_art_base64 && createPortal(
        <div
          className="fixed inset-0 z-[9999] flex items-center justify-center p-4 bg-black/85 backdrop-blur-md"
          style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, width: '100vw', height: '100vh' }}
          onClick={() => setShowCoverModal(false)}
        >
          <div
            className="relative max-w-md w-full bg-slate-900 border border-white/20 rounded-2xl p-5 shadow-2xl overflow-hidden flex flex-col items-center my-auto"
            onClick={(e) => e.stopPropagation()}
          >
            <button
              onClick={() => setShowCoverModal(false)}
              className="absolute top-3 right-3 p-1.5 rounded-full bg-black/60 hover:bg-white/20 text-white/80 hover:text-white transition-colors cursor-pointer"
              title="Đóng"
            >
              <X size={18} />
            </button>

            <div className="w-full aspect-square max-w-[360px] rounded-xl overflow-hidden shadow-2xl border border-white/10 relative mt-2 bg-black">
              <img
                src={metadata.cover_art_base64}
                alt={metadata.title || filename}
                className="w-full h-full object-contain"
              />
            </div>

            <div className="mt-4 text-center w-full">
              <h3 className="text-base font-bold text-white truncate">
                {metadata.title || filename}
              </h3>
              {metadata.artist && (
                <p className="text-sm text-cyan-400 font-medium truncate mt-0.5">
                  {metadata.artist}
                </p>
              )}
              {metadata.album && (
                <p className="text-xs text-slate-400 truncate mt-0.5 italic">
                  {metadata.album}
                </p>
              )}
            </div>
          </div>
        </div>,
        document.body
      )}
    </>
  );
}
