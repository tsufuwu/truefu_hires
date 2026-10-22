// components/LanguageSwitch.tsx
import { Languages } from 'lucide-react';
import type { Language } from '../i18n';

interface Props {
  currentLang: Language;
  onLanguageChange: (lang: Language) => void;
}

export function LanguageSwitch({ currentLang, onLanguageChange }: Props) {
  return (
    <div
      className="inline-flex items-center p-1 rounded-xl border transition-all"
      style={{
        background: 'rgba(17, 24, 38, 0.85)',
        borderColor: 'rgba(99, 130, 201, 0.25)',
        boxShadow: '0 2px 10px rgba(0, 0, 0, 0.3)',
      }}
    >
      <div className="pl-1.5 pr-1 text-slate-400">
        <Languages size={14} className="text-cyan-400" />
      </div>

      <button
        type="button"
        onClick={() => onLanguageChange('vi')}
        className={`px-2.5 py-1 rounded-lg text-xs font-bold transition-all flex items-center gap-1.5 ${
          currentLang === 'vi'
            ? 'shadow-md'
            : 'text-slate-400 hover:text-slate-200'
        }`}
        style={
          currentLang === 'vi'
            ? {
                background: 'linear-gradient(135deg, rgba(0, 229, 255, 0.2), rgba(59, 130, 246, 0.3))',
                color: '#00e5ff',
                border: '1px solid rgba(0, 229, 255, 0.4)',
                boxShadow: '0 0 12px rgba(0, 229, 255, 0.25)',
              }
            : {
                background: 'transparent',
                border: '1px solid transparent',
              }
        }
      >
        <span>🇻🇳</span>
        <span>Tiếng Việt</span>
      </button>

      <button
        type="button"
        onClick={() => onLanguageChange('en')}
        className={`px-2.5 py-1 rounded-lg text-xs font-bold transition-all flex items-center gap-1.5 ${
          currentLang === 'en'
            ? 'shadow-md'
            : 'text-slate-400 hover:text-slate-200'
        }`}
        style={
          currentLang === 'en'
            ? {
                background: 'linear-gradient(135deg, rgba(0, 229, 255, 0.2), rgba(59, 130, 246, 0.3))',
                color: '#00e5ff',
                border: '1px solid rgba(0, 229, 255, 0.4)',
                boxShadow: '0 0 12px rgba(0, 229, 255, 0.25)',
              }
            : {
                background: 'transparent',
                border: '1px solid transparent',
              }
        }
      >
        <span>🇬🇧</span>
        <span>English</span>
      </button>
    </div>
  );
}
