import React, { useState, useEffect } from 'react';
import { Rocket, Clock, Play, Pause, RotateCcw } from 'lucide-react';

interface FlightPhaseOverlayProps {
  currentTimestamp: number;
}

export const FlightPhaseOverlay: React.FC<FlightPhaseOverlayProps> = ({ currentTimestamp: initialTs }) => {
  const [overrideTs, setOverrideTs] = useState<number | null>(null);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);

  const effectiveTs = overrideTs !== null ? overrideTs : initialTs;

  const phases = [
    { name: 'PRE_LAUNCH', label: 'Pre-Launch', start: 0, end: 10, gradient: 'linear-gradient(135deg, #3b82f6, #6366f1)' },
    { name: 'LIFTOFF', label: 'Liftoff', start: 10, end: 60, gradient: 'linear-gradient(135deg, #f97316, #ef4444)' },
    { name: 'MAX_Q', label: 'Max-Q', start: 60, end: 90, gradient: 'linear-gradient(135deg, #ef4444, #ec4899)' },
    { name: 'STAGE_1_FLIGHT', label: 'Stage 1', start: 90, end: 150, gradient: 'linear-gradient(135deg, #eab308, #f97316)' },
    { name: 'STAGE_SEPARATION', label: 'Stage Sep', start: 150, end: 160, gradient: 'linear-gradient(135deg, #8b5cf6, #a855f7)' },
    { name: 'STAGE_2_FLIGHT', label: 'Stage 2', start: 160, end: 450, gradient: 'linear-gradient(135deg, #06b6d4, #3b82f6)' },
    { name: 'COAST_ORBIT', label: 'Coast / Orbit', start: 450, end: 600, gradient: 'linear-gradient(135deg, #10b981, #06b6d4)' },
  ];

  // Sync override with external updates when not playing
  useEffect(() => {
    if (!isPlaying && overrideTs === null) {
      setOverrideTs(initialTs);
    }
  }, [initialTs, isPlaying]);

  // Live animation interval when playing
  useEffect(() => {
    let interval: any = null;
    if (isPlaying) {
      interval = setInterval(() => {
        setOverrideTs((prev) => {
          const current = prev !== null ? prev : initialTs;
          const next = current + 2.0;
          return next > 600.0 ? 0.0 : next;
        });
      }, 100);
    } else {
      clearInterval(interval);
    }
    return () => clearInterval(interval);
  }, [isPlaying, initialTs]);

  const getActivePhase = () =>
    phases.find((p) => effectiveTs >= p.start && effectiveTs <= p.end) || phases[0];

  const activePhase = getActivePhase();
  const progressPct = Math.min(100, Math.max(0, (effectiveTs / 600) * 100));

  const handleTrackClick = (e: React.MouseEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const pct = Math.max(0, Math.min(1, clickX / rect.width));
    setOverrideTs(roundOne(pct * 600.0));
  };

  const roundOne = (val: number) => Math.round(val * 10) / 10;

  return (
    <div className="glass-panel p-5">
      {/* Top Bar */}
      <div className="flex flex-wrap items-center justify-between mb-4 text-xs gap-2">
        <div className="flex items-center space-x-2 font-bold" style={{ color: 'var(--text-main)' }}>
          <Rocket className="w-4 h-4" style={{ color: 'var(--isro-orange)' }} />
          <span className="tracking-wide uppercase text-sm">Launch Vehicle Flight Timeline</span>
          <span
            className="px-2.5 py-0.5 rounded-lg font-mono text-[10px]"
            style={{
              background: 'var(--pill-bg)',
              color: 'var(--text-muted)',
              border: '1px solid var(--pill-border)',
            }}
          >
            0 – 600s
          </span>
        </div>

        <div className="flex items-center space-x-2.5">
          {/* Live Playback Controls */}
          <button
            onClick={() => setIsPlaying(!isPlaying)}
            className="flex items-center space-x-1 px-2.5 py-1.5 rounded-xl text-white font-mono text-[11px] font-bold transition-all"
            style={{
              background: isPlaying ? 'linear-gradient(135deg, #ef4444, #dc2626)' : 'linear-gradient(135deg, #10b981, #059669)',
              boxShadow: '0 2px 10px rgba(0,0,0,0.2)',
            }}
            title={isPlaying ? 'Pause Playback' : 'Play Mission Timeline Simulation'}
          >
            {isPlaying ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5 fill-current" />}
            <span>{isPlaying ? 'PAUSE' : 'PLAY'}</span>
          </button>

          <button
            onClick={() => { setOverrideTs(0.0); setIsPlaying(false); }}
            className="p-1.5 rounded-xl transition-all"
            style={{
              background: 'var(--pill-bg)',
              color: 'var(--text-muted)',
              border: '1px solid var(--pill-border)',
            }}
            title="Reset Scrubber to T+0.0s"
          >
            <RotateCcw className="w-3.5 h-3.5" />
          </button>

          {/* Mission Elapsed */}
          <div
            className="flex items-center space-x-1.5 px-3 py-1.5 rounded-xl"
            style={{
              background: 'rgba(249, 115, 22, 0.08)',
              border: '1px solid rgba(249, 115, 22, 0.2)',
            }}
          >
            <Clock className="w-3.5 h-3.5" style={{ color: 'var(--isro-orange)' }} />
            <span className="text-[11px] font-semibold" style={{ color: 'var(--text-muted)' }}>MET:</span>
            <span className="font-mono font-bold text-xs" style={{ color: 'var(--isro-orange)' }}>
              T+{effectiveTs.toFixed(1)}s
            </span>
          </div>

          {/* Active Phase */}
          <div
            className="flex items-center space-x-1.5 px-3 py-1.5 rounded-xl"
            style={{
              background: 'rgba(6, 182, 212, 0.08)',
              border: '1px solid rgba(6, 182, 212, 0.2)',
            }}
          >
            <span className="w-2 h-2 rounded-full animate-pulse" style={{ background: 'var(--accent-cyan)' }} />
            <span className="text-[11px] font-semibold" style={{ color: 'var(--text-muted)' }}>PHASE:</span>
            <span className="font-mono font-bold text-xs" style={{ color: 'var(--accent-cyan)' }}>
              {activePhase.name}
            </span>
          </div>
        </div>
      </div>

      {/* Progress Track */}
      <div className="relative pt-1 cursor-pointer" onClick={handleTrackClick}>
        {/* Scrubber Pin */}
        <div
          className="absolute top-0 bottom-0 w-0.5 z-20 transition-all duration-150 pointer-events-none"
          style={{
            left: `${progressPct}%`,
            background: 'var(--isro-orange)',
            boxShadow: '0 0 10px rgba(249, 115, 22, 0.8)',
          }}
        >
          <div
            className="w-3.5 h-3.5 rounded-full -ml-1.5 -mt-1 shadow-lg"
            style={{
              background: 'var(--isro-orange)',
              border: '2px solid #ffffff',
              boxShadow: '0 0 12px rgba(249, 115, 22, 0.9)',
            }}
          />
        </div>

        <div
          className="w-full h-9 rounded-xl p-1 flex space-x-1 overflow-hidden"
          style={{
            background: 'var(--pill-bg)',
            border: '1px solid var(--pill-border)',
          }}
        >
          {phases.map((p) => {
            const widthPct = ((p.end - p.start) / 600) * 100;
            const isActive = activePhase.name === p.name;
            return (
              <div
                key={p.name}
                onClick={(e) => {
                  e.stopPropagation();
                  setOverrideTs(p.start);
                }}
                style={{
                  width: `${widthPct}%`,
                  background: isActive ? p.gradient : 'transparent',
                  boxShadow: isActive ? '0 2px 10px rgba(0,0,0,0.2)' : 'none',
                }}
                className="h-full rounded-lg transition-all relative group cursor-pointer flex items-center justify-center"
              >
                <span
                  className="text-[10px] font-mono font-bold truncate px-1 tracking-tight"
                  style={{
                    color: isActive ? '#fff' : 'var(--text-muted)',
                  }}
                >
                  {p.label}
                </span>

                {/* Tooltip */}
                <div
                  className="absolute hidden group-hover:block bottom-11 left-1/2 transform -translate-x-1/2 p-2.5 rounded-xl z-50 whitespace-nowrap text-[11px]"
                  style={{
                    background: 'var(--tooltip-bg)',
                    border: '1px solid var(--card-border)',
                    boxShadow: '0 10px 30px rgba(0,0,0,0.3)',
                    backdropFilter: 'blur(12px)',
                  }}
                >
                  <div className="font-bold" style={{ color: 'var(--isro-orange)' }}>{p.name}</div>
                  <div className="text-[10px] font-mono" style={{ color: 'var(--text-muted)' }}>
                    T+{p.start}s → T+{p.end}s
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
