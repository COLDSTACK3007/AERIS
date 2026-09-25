import React, { useEffect, useState } from 'react';
import { api } from '../../services/api';
import { TrendingUp, AlertTriangle, CheckCircle, Clock, Activity, HelpCircle } from 'lucide-react';

export const DriftMonitor: React.FC = () => {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    api.getDriftAnalysis()
      .then((res) => {
        setData(res);
        setLoading(false);
      })
      .catch(() => {
        setLoading(false);
      });
  }, []);

  const results = data?.results || [];

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'approaching_threshold':
        return { label: 'CRITICAL DRIFT', bg: 'rgba(244, 63, 94, 0.15)', color: '#fb7185', border: 'rgba(244, 63, 94, 0.3)' };
      case 'trending':
        return { label: 'TRENDING', bg: 'rgba(245, 158, 11, 0.15)', color: '#fbbf24', border: 'rgba(245, 158, 11, 0.3)' };
      default:
        return { label: 'STABLE', bg: 'rgba(16, 185, 129, 0.15)', color: '#34d399', border: 'rgba(16, 185, 129, 0.3)' };
    }
  };

  return (
    <div className="glass-panel p-3 sm:p-4 flex flex-col h-[280px] sm:h-[320px]">
      {/* Header */}
      <div
        className="flex items-center justify-between mb-3 pb-2.5"
        style={{ borderBottom: '1px solid var(--divider)' }}
      >
        <div className="flex items-center space-x-2.5">
          <div
            className="p-2 rounded-xl"
            style={{
              background: 'rgba(168, 85, 247, 0.08)',
              border: '1px solid rgba(168, 85, 247, 0.2)',
            }}
          >
            <TrendingUp className="w-4 h-4 text-purple-400" />
          </div>
          <div>
            <h2 className="text-sm font-bold uppercase tracking-wider" style={{ color: 'var(--text-main)' }}>
              Predictive Drift Monitor
            </h2>
            <p className="text-[10px] font-mono" style={{ color: 'var(--text-muted)' }}>
              Linear Regression Rolling Trend & Threshold Crossing Prediction
            </p>
          </div>
        </div>

        <div className="text-[10px] font-mono px-2 py-1 rounded-lg bg-slate-900 border border-slate-800 text-slate-300">
          Window: <span className="text-amber-400">30s</span> | R² Min: <span className="text-cyan-400">0.60</span>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto pr-1 space-y-2 text-xs">
        {loading ? (
          <div className="h-full flex items-center justify-center text-slate-400 font-mono">
            Analyzing telemetry trends...
          </div>
        ) : results.length === 0 ? (
          <div className="h-full flex items-center justify-center text-slate-500 font-mono">
            No drift trends detected.
          </div>
        ) : (
          results.map((r: any, idx: number) => {
            const badge = getStatusBadge(r.trend_status);
            return (
              <div
                key={idx}
                className="p-3 rounded-xl transition-all space-y-2"
                style={{
                  background: r.trend_status === 'approaching_threshold' ? 'rgba(244, 63, 94, 0.06)' : 'rgba(255, 255, 255, 0.02)',
                  border: `1px solid ${r.trend_status === 'approaching_threshold' ? 'rgba(244, 63, 94, 0.25)' : 'rgba(255, 255, 255, 0.05)'}`,
                }}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <span className="font-bold text-slate-200 text-xs">{r.parameter}</span>
                    <span className="text-[10px] font-mono text-slate-400">({r.unit})</span>
                  </div>

                  <span
                    className="text-[10px] font-mono font-bold px-2 py-0.5 rounded-md uppercase"
                    style={{ background: badge.bg, color: badge.color, border: `1px solid ${badge.border}` }}
                  >
                    {badge.label}
                  </span>
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-[11px] font-mono">
                  <div className="p-2 rounded-lg bg-black/40">
                    <span className="text-slate-400 text-[9px] block uppercase">Current Value</span>
                    <span className="font-bold text-sky-400">{r.current_value}</span>
                  </div>

                  <div className="p-2 rounded-lg bg-black/40">
                    <span className="text-slate-400 text-[9px] block uppercase">Drift Slope</span>
                    <span className={`font-bold ${r.slope_per_second > 0 ? 'text-amber-400' : 'text-cyan-400'}`}>
                      {r.slope_per_second > 0 ? `+${r.slope_per_second}` : r.slope_per_second}/s
                    </span>
                  </div>

                  <div className="p-2 rounded-lg bg-black/40">
                    <span className="text-slate-400 text-[9px] block uppercase">R² Fit Confidence</span>
                    <span className="font-bold text-emerald-400">{(r.r_squared * 100).toFixed(1)}%</span>
                  </div>

                  <div className="p-2 rounded-lg bg-black/40">
                    <span className="text-slate-400 text-[9px] block uppercase">Crossing Estimate</span>
                    {r.time_to_crossing !== null && r.time_to_crossing !== undefined ? (
                      <span className="font-bold text-rose-400 flex items-center space-x-1">
                        <Clock className="w-3 h-3 inline" />
                        <span>~{r.time_to_crossing}s</span>
                      </span>
                    ) : (
                      <span className="text-slate-500 italic text-[10px]">No imminent breach</span>
                    )}
                  </div>
                </div>

                {r.time_to_crossing !== null && (
                  <p className="text-[10px] text-rose-300 font-mono flex items-center space-x-1 bg-rose-500/10 p-1.5 rounded border border-rose-500/20">
                    <AlertTriangle className="w-3 h-3 flex-shrink-0" />
                    <span>
                      Predicted {r.crossing_direction} threshold violation ({r.crossing_threshold} {r.unit}) in{' '}
                      <strong>{r.time_to_crossing} seconds</strong> at current drift trajectory.
                    </span>
                  </p>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
