// MiniAudioPlayer.tsx — Compact Audiophile Media Player right below album cover art
import { useState, useRef, useEffect, useCallback } from 'react';
import { Play, Pause, Volume2, VolumeX, AlertCircle } from 'lucide-react';

interface Props {
  audioUrl: string | null;
  durationSec?: number;
  isDsd?: boolean;
  lang?: string;
}

function formatTime(seconds: number): string {
  if (isNaN(seconds) || seconds < 0) return '0:00';
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs < 10 ? '0' : ''}${secs}`;
}

export function MiniAudioPlayer({ audioUrl, durationSec = 0, isDsd = false, lang = 'vi' }: Props) {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const progressBarRef = useRef<HTMLDivElement | null>(null);

  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [totalDuration, setTotalDuration] = useState(durationSec || 0);
  const [isMuted, setIsMuted] = useState(false);
  const [playbackError, setPlaybackError] = useState<string | null>(null);

  // Sync total duration if prop changes
  useEffect(() => {
    if (durationSec > 0 && (!totalDuration || totalDuration === 0)) {
      setTotalDuration(durationSec);
    }
  }, [durationSec, totalDuration]);

  // Reset state when audio URL changes
  useEffect(() => {
    setIsPlaying(false);
    setCurrentTime(0);
    setPlaybackError(null);
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
    }
  }, [audioUrl]);

  const togglePlay = useCallback(() => {
    if (!audioRef.current || !audioUrl) return;

    if (isDsd) {
      setPlaybackError(
        lang === 'vi'
          ? 'DSD Bitstream cần giải mã DAC ngoài'
          : 'DSD Direct requires external hardware DAC'
      );
      return;
    }

    if (isPlaying) {
      audioRef.current.pause();
      setIsPlaying(false);
    } else {
      setPlaybackError(null);
      const playPromise = audioRef.current.play();
      if (playPromise !== undefined) {
        playPromise
          .then(() => {
            setIsPlaying(true);
          })
          .catch((err) => {
            console.warn('Audio playback error:', err);
            setIsPlaying(false);
            setPlaybackError(
              lang === 'vi'
                ? 'Không thể giải mã trực tiếp codec này'
                : 'Browser cannot decode this codec directly'
            );
          });
      }
    }
  }, [audioUrl, isDsd, isPlaying, lang]);

  const handleTimeUpdate = () => {
    if (audioRef.current) {
      setCurrentTime(audioRef.current.currentTime);
      if (audioRef.current.duration && !isNaN(audioRef.current.duration)) {
        setTotalDuration(audioRef.current.duration);
      }
    }
  };

  const handleEnded = () => {
    setIsPlaying(false);
    setCurrentTime(0);
    if (audioRef.current) {
      audioRef.current.currentTime = 0;
    }
  };

  const toggleMute = () => {
    if (audioRef.current) {
      audioRef.current.muted = !isMuted;
      setIsMuted(!isMuted);
    }
  };

  const handleSeek = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!progressBarRef.current || !audioRef.current) return;
    const rect = progressBarRef.current.getBoundingClientRect();
    const pos = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
    const targetTime = pos * (totalDuration || durationSec || 1);
    setCurrentTime(targetTime);
    audioRef.current.currentTime = targetTime;
  };

  const progressPercent = totalDuration > 0
    ? Math.min(100, Math.max(0, (currentTime / totalDuration) * 100))
    : 0;

  if (!audioUrl) return null;

  return (
    <div
      className="w-full max-w-[130px] sm:max-w-[145px] rounded-xl p-2 flex flex-col gap-1.5 transition-all duration-300"
      style={{
        background: 'rgba(10, 15, 26, 0.92)',
        border: isPlaying ? '1px solid rgba(0, 229, 255, 0.4)' : '1px solid rgba(99, 130, 201, 0.2)',
        boxShadow: isPlaying
          ? '0 0 16px rgba(0, 229, 255, 0.18), inset 0 0 10px rgba(0, 229, 255, 0.05)'
          : '0 4px 12px rgba(0, 0, 0, 0.4)',
      }}
    >
      <audio
        ref={audioRef}
        src={audioUrl}
        preload="metadata"
        onTimeUpdate={handleTimeUpdate}
        onEnded={handleEnded}
        onError={() => {
          setIsPlaying(false);
          setPlaybackError(
            isDsd
              ? (lang === 'vi' ? 'DSD bitstream (cần DAC)' : 'DSD Direct (Hardware DAC required)')
              : (lang === 'vi' ? 'Lỗi phát âm thanh' : 'Playback error')
          );
        }}
      />

      {/* Top Row: Mini scrubber bar */}
      <div
        ref={progressBarRef}
        onClick={handleSeek}
        className="w-full h-1.5 bg-slate-800 rounded-full relative cursor-pointer group flex items-center overflow-hidden"
        title={lang === 'vi' ? 'Tua nhạc' : 'Seek'}
      >
        <div
          className="h-full rounded-full transition-[width] duration-100"
          style={{
            width: `${progressPercent}%`,
            background: isPlaying
              ? 'linear-gradient(90deg, #00e5ff, #3b82f6)'
              : 'rgba(148, 163, 184, 0.6)',
            boxShadow: isPlaying ? '0 0 8px rgba(0, 229, 255, 0.6)' : 'none',
          }}
        />
      </div>

      {/* Bottom Row: Play/Pause button + Time + Mute */}
      <div className="flex items-center justify-between gap-1">
        {/* Play/Pause Button */}
        <button
          type="button"
          onClick={togglePlay}
          className="w-6 h-6 rounded-full flex items-center justify-center shrink-0 transition-transform active:scale-95 cursor-pointer"
          style={{
            background: isPlaying
              ? 'rgba(0, 229, 255, 0.2)'
              : 'rgba(255, 255, 255, 0.08)',
            border: isPlaying
              ? '1px solid rgba(0, 229, 255, 0.5)'
              : '1px solid rgba(255, 255, 255, 0.15)',
            color: isPlaying ? '#00e5ff' : '#e2e8f0',
            boxShadow: isPlaying ? '0 0 10px rgba(0, 229, 255, 0.3)' : 'none',
          }}
          title={isPlaying ? (lang === 'vi' ? 'Tạm dừng' : 'Pause') : (lang === 'vi' ? 'Phát thử' : 'Play preview')}
        >
          {isPlaying ? (
            <Pause size={10} className="fill-cyan-400 stroke-cyan-400" />
          ) : (
            <Play size={10} className="ml-0.5 fill-slate-200 stroke-slate-200" />
          )}
        </button>

        {/* Time display */}
        <div className="flex items-center gap-1 min-w-0">
          <span className="text-[10px] mono font-semibold text-slate-300 truncate">
            {formatTime(currentTime)}
          </span>
          <span className="text-[9px] text-slate-500">/</span>
          <span className="text-[10px] mono font-medium text-slate-400 truncate">
            {formatTime(totalDuration || durationSec)}
          </span>
        </div>

        {/* Mute button or dancing mini visualizer when playing */}
        <div className="flex items-center shrink-0">
          {isPlaying ? (
            <div className="flex items-end gap-0.5 h-3 px-1" title="Playing">
              <span className="w-0.5 bg-cyan-400 rounded-full animate-pulse" style={{ height: '60%' }} />
              <span className="w-0.5 bg-cyan-300 rounded-full animate-pulse" style={{ height: '100%', animationDelay: '150ms' }} />
              <span className="w-0.5 bg-cyan-400 rounded-full animate-pulse" style={{ height: '40%', animationDelay: '300ms' }} />
            </div>
          ) : (
            <button
              type="button"
              onClick={toggleMute}
              className="p-1 text-slate-400 hover:text-slate-200 transition-colors cursor-pointer"
              title={isMuted ? (lang === 'vi' ? 'Bật tiếng' : 'Unmute') : (lang === 'vi' ? 'Tắt tiếng' : 'Mute')}
            >
              {isMuted ? <VolumeX size={12} className="text-rose-400" /> : <Volume2 size={12} />}
            </button>
          )}
        </div>
      </div>

      {/* Error / Format notice */}
      {playbackError && (
        <div className="text-[9px] text-amber-300 flex items-center gap-1 leading-tight pt-0.5 border-t border-amber-500/20">
          <AlertCircle size={10} className="shrink-0 text-amber-400" />
          <span className="truncate">{playbackError}</span>
        </div>
      )}
    </div>
  );
}
