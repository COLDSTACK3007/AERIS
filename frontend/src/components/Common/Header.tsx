import React from 'react';
import { Activity, Cpu, RefreshCw, Sun, Moon, Upload, Satellite } from 'lucide-react';

interface HeaderProps {
  onRefresh: () => void;
  onGenerateSynthetic: () => void;
  onUploadCSV?: (file: File) => void;
  isGenerating: boolean;
  activeFlightPhase: string;
  theme: 'dark' | 'light';
  toggleTheme: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  onRefresh,
  onGenerateSynthetic,
  onUploadCSV,
  isGenerating,
  activeFlightPhase,
  theme,
  toggleTheme
}) => {
  const fileInputRef = React.useRef<HTMLInputElement>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0] && onUploadCSV) {
      onUploadCSV(e.target.files[0]);
    }
    e.target.value = '';
  };

  return (
    <header className="glass-panel px-3.5 sm:px-6 py-3 sm:py-4 mb-4 sm:mb-6 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 sm:gap-4">
      {/* Left: Brand */}
      <div className="flex items-center space-x-3 w-full sm:w-auto justify-between sm:justify-start">
        <div className="flex items-center space-x-3">
          <div
            className="w-9 h-9 sm:w-11 sm:h-11 rounded-xl sm:rounded-2xl flex items-center justify-center shadow-lg relative overflow-hidden flex-shrink-0"
            style={{
              background: 'linear-gradient(135deg, #f97316, #f59e0b, #eab308)',
              boxShadow: '0 4px 20px -2px rgba(249, 115, 22, 0.4)',
            }}
          >
            <Satellite className="w-4 h-4 sm:w-5 sm:h-5 text-white relative z-10" />
            <div className="absolute inset-0 bg-white/10 animate-shimmer" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h1
                className="text-lg sm:text-xl font-black tracking-widest"
                style={{ color: 'var(--text-main)', letterSpacing: '0.15em' }}
              >
                AERIS
              </h1>
              <span
                className="text-[9px] sm:text-[10px] px-2 py-0.5 sm:py-1 rounded-lg font-bold font-mono"
                style={{
                  background: 'rgba(249, 115, 22, 0.1)',
                  color: 'var(--isro-orange)',
                  border: '1px solid rgba(249, 115, 22, 0.25)',
                }}
              >
                ISRO SIH2026170
              </span>
            </div>
            <p className="text-[10px] sm:text-[11px] font-medium mt-0.5 line-clamp-1" style={{ color: 'var(--text-muted)' }}>
              Physics-Constrained Telemetry Processing & Data Imputation
            </p>
          </div>
        </div>

        {/* Mobile-only theme toggle shortcut */}
        <button
          onClick={toggleTheme}
          className="sm:hidden p-2 rounded-xl transition-all flex items-center justify-center"
          style={{
            background: 'var(--pill-bg)',
            border: '1px solid var(--pill-border)',
            color: theme === 'dark' ? '#fbbf24' : '#2563eb',
          }}
          title={`Switch to ${theme === 'dark' ? 'Light' : 'Dark'} Theme`}
        >
          {theme === 'dark' ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
        </button>
      </div>

      {/* Right: Controls */}
      <div className="flex flex-wrap items-center gap-2 sm:gap-2.5 w-full sm:w-auto">
        {/* Active Phase Indicator */}
        <div
          className="flex items-center space-x-1.5 px-2.5 sm:px-3 py-1.5 sm:py-2 rounded-xl"
          style={{
            background: 'var(--pill-bg)',
            border: '1px solid var(--pill-border)',
          }}
        >
          <Cpu className="w-3 h-3 sm:w-3.5 sm:h-3.5 animate-pulse" style={{ color: 'var(--accent-cyan)' }} />
          <span className="text-[9px] sm:text-[10px] font-mono font-semibold" style={{ color: 'var(--text-muted)' }}>
            PHASE:
          </span>
          <span className="text-[10px] sm:text-[11px] font-mono font-bold" style={{ color: 'var(--accent-cyan)' }}>
            {activeFlightPhase}
          </span>
        </div>

        <input
          type="file"
          ref={fileInputRef}
          onChange={handleFileChange}
          accept=".csv"
          className="hidden"
        />

        {/* Upload CSV */}
        <button
          onClick={() => fileInputRef.current?.click()}
          className="flex items-center space-x-1.5 text-[11px] sm:text-xs font-bold px-3 py-1.5 sm:py-2 rounded-xl transition-all"
          style={{
            background: 'var(--pill-bg)',
            color: 'var(--text-main)',
            border: '1px solid var(--pill-border)',
          }}
          title="Upload Multi-Rate Telemetry CSV File"
        >
          <Upload className="w-3.5 h-3.5" style={{ color: 'var(--accent-cyan)' }} />
          <span>Upload CSV</span>
        </button>

        {/* Simulate Mission */}
        <button
          onClick={onGenerateSynthetic}
          disabled={isGenerating}
          className="flex items-center space-x-1.5 text-white text-[11px] sm:text-xs font-bold px-3 sm:px-4 py-1.5 sm:py-2 rounded-xl transition-all disabled:opacity-50"
          style={{
            background: 'linear-gradient(135deg, #f97316, #f59e0b)',
            boxShadow: '0 4px 14px -2px rgba(249, 115, 22, 0.35)',
          }}
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isGenerating ? 'animate-spin' : ''}`} />
          <span>{isGenerating ? 'Simulating...' : 'Simulate 600s Mission'}</span>
        </button>

        {/* Theme Toggle (Desktop) */}
        <button
          onClick={toggleTheme}
          className="hidden sm:flex p-2.5 rounded-xl transition-all items-center justify-center"
          style={{
            background: 'var(--pill-bg)',
            border: '1px solid var(--pill-border)',
            color: theme === 'dark' ? '#fbbf24' : '#2563eb',
          }}
          title={`Switch to ${theme === 'dark' ? 'Light' : 'Dark'} Theme`}
        >
          {theme === 'dark' ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
        </button>

        {/* Refresh */}
        <button
          onClick={onRefresh}
          className="p-2 sm:p-2.5 rounded-xl transition-all"
          style={{
            background: 'var(--pill-bg)',
            color: 'var(--text-muted)',
            border: '1px solid var(--pill-border)',
          }}
          title="Refresh Data"
        >
          <RefreshCw className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
        </button>
      </div>
    </header>
  );
};
