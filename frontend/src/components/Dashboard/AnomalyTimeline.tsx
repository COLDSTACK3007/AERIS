import React, { useState } from 'react';
import { AnomalyItem } from '../../types/telemetry';
import { AlertTriangle, AlertCircle, Zap, Search } from 'lucide-react';

interface AnomalyTimelineProps {
  anomalies: AnomalyItem[];
  onRunDetection: () => void;
  isDetecting: boolean;
  onSelectAnomaly?: (anomalyId: number) => void;
}

export const AnomalyTimeline: React.FC<AnomalyTimelineProps> = ({
  anomalies,
  onRunDetection,
  isDetecting,
  onSelectAnomaly,
}) => {
  const [filterType, setFilterType] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState<string>('');

  const filteredAnomalies = anomalies.filter((a) => {
    const matchesType = filterType === 'ALL' || a.anomaly_type === filterType;
    const matchesSearch =
      searchQuery === '' ||
      a.parameter.toLowerCase().includes(searchQuery.toLowerCase()) ||
      a.description.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesType && matchesSearch;
  });

  const getSeverityStyle = (severity: string) => {
    switch (severity) {
      case 'CRITICAL':
        return { bg: 'rgba(244, 63, 94, 0.1)', color: '#fb7185', border: 'rgba(244, 63, 94, 0.2)' };
      case 'WARNING':
        return { bg: 'rgba(245, 158, 11, 0.1)', color: '#fbbf24', border: 'rgba(245, 158, 11, 0.2)' };
      default:
        return { bg: 'rgba(59, 130, 246, 0.1)', color: '#60a5fa', border: 'rgba(59, 130, 246, 0.2)' };
    }
  };

  const getTypeStyle = (type: string) => {
    const styles: Record<string, { color: string; bg: string; border: string }> = {
      GAP: { color: '#a78bfa', bg: 'rgba(139, 92, 246, 0.08)', border: 'rgba(139, 92, 246, 0.2)' },
      DRIFT: { color: '#fbbf24', bg: 'rgba(245, 158, 11, 0.08)', border: 'rgba(245, 158, 11, 0.2)' },
      NOISE: { color: '#22d3ee', bg: 'rgba(6, 182, 212, 0.08)', border: 'rgba(6, 182, 212, 0.2)' },
      STUCK: { color: '#fb7185', bg: 'rgba(244, 63, 94, 0.08)', border: 'rgba(244, 63, 94, 0.2)' },
      SPIKE: { color: '#facc15', bg: 'rgba(250, 204, 21, 0.08)', border: 'rgba(250, 204, 21, 0.2)' },
      PHYSICS_VIOLATION: { color: '#34d399', bg: 'rgba(16, 185, 129, 0.08)', border: 'rgba(16, 185, 129, 0.2)' },
    };
    return styles[type] || styles.PHYSICS_VIOLATION;
  };

  return (
    <div className="glass-panel p-3.5 sm:p-5 flex flex-col h-[380px] sm:h-[420px]">
      {/* Header */}
      <div
        className="flex flex-wrap items-center justify-between mb-3 pb-2.5 gap-2"
        style={{ borderBottom: '1px solid var(--divider)' }}
      >
        <div className="flex items-center space-x-2.5">
          <div
            className="p-2 rounded-xl"
            style={{
              background: 'rgba(245, 158, 11, 0.08)',
              border: '1px solid rgba(245, 158, 11, 0.2)',
            }}
          >
            <AlertTriangle className="w-4 h-4" style={{ color: '#f59e0b' }} />
          </div>
          <div>
            <h2 className="text-sm font-bold uppercase tracking-wider" style={{ color: 'var(--text-main)' }}>
              Anomaly Classifier ({anomalies.length})
            </h2>
            <p className="text-[10px] font-mono" style={{ color: 'var(--text-muted)' }}>
              Multi-Strategy Failure Mode Catalog
            </p>
          </div>
        </div>

        <button
          onClick={onRunDetection}
          disabled={isDetecting}
          className="flex items-center space-x-2 text-white text-xs font-bold px-3.5 py-2 rounded-xl transition-all disabled:opacity-50"
          style={{
            background: 'linear-gradient(135deg, #f59e0b, #f97316)',
            boxShadow: '0 4px 14px -2px rgba(245, 158, 11, 0.35)',
          }}
        >
          <Zap className={`w-3.5 h-3.5 ${isDetecting ? 'animate-spin' : ''}`} />
          <span>{isDetecting ? 'Scanning...' : 'Run Detector'}</span>
        </button>
      </div>

      {/* Filter & Search */}
      <div className="flex flex-wrap items-center justify-between gap-2 mb-3 text-xs">
        <div className="flex items-center space-x-1 overflow-x-auto py-0.5">
          {['ALL', 'GAP', 'DRIFT', 'NOISE', 'STUCK', 'SPIKE', 'PHYSICS_VIOLATION'].map((type) => (
            <button
              key={type}
              onClick={() => setFilterType(type)}
              className="text-[10px] font-mono px-2.5 py-1 rounded-lg transition-all font-bold"
              style={{
                background: filterType === type ? 'rgba(249, 115, 22, 0.1)' : 'var(--pill-bg)',
                color: filterType === type ? 'var(--isro-orange)' : 'var(--text-muted)',
                border: `1px solid ${filterType === type ? 'rgba(249, 115, 22, 0.3)' : 'var(--pill-border)'}`,
              }}
            >
              {type}
            </button>
          ))}
        </div>

        <div className="relative">
          <Search className="w-3.5 h-3.5 absolute left-2.5 top-2" style={{ color: 'var(--text-muted)' }} />
          <input
            type="text"
            placeholder="Search anomaly..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="rounded-xl text-[11px] pl-8 pr-2.5 py-1.5 focus:outline-none w-36"
            style={{
              background: 'var(--input-bg)',
              color: 'var(--text-main)',
              border: '1px solid var(--pill-border)',
            }}
          />
        </div>
      </div>

      {/* Anomaly List */}
      <div className="flex-1 overflow-y-auto space-y-2 pr-1">
        {filteredAnomalies.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-xs py-10" style={{ color: 'var(--text-muted)' }}>
            <AlertCircle className="w-8 h-8 mb-2 animate-pulse" />
            <span>No anomalies found. Run the detector to scan telemetry feed.</span>
          </div>
        ) : (
          filteredAnomalies.map((anom, i) => {
            const typeStyle = getTypeStyle(anom.anomaly_type);
            const sevStyle = getSeverityStyle(anom.severity);
            return (
              <div
                key={i}
                onClick={() => anom.id && onSelectAnomaly && onSelectAnomaly(anom.id)}
                className="p-3 rounded-xl transition-all flex items-start justify-between text-xs cursor-pointer hover:border-amber-500/40 hover:bg-slate-800/60 group"
                style={{
                  background: 'var(--pill-bg)',
                  border: '1px solid var(--pill-border)',
                }}
              >
                <div className="space-y-1.5">
                  <div className="flex items-center space-x-2 flex-wrap">
                    <span className="font-mono font-bold text-xs" style={{ color: 'var(--isro-orange)' }}>
                      T+{anom.timestamp.toFixed(1)}s
                    </span>
                    <span className="font-bold tracking-wide group-hover:text-amber-300 transition-colors" style={{ color: 'var(--text-main)' }}>
                      {anom.parameter}
                    </span>
                    <span
                      className="font-mono text-[10px] font-bold px-2 py-0.5 rounded-md"
                      style={{
                        color: typeStyle.color,
                        background: typeStyle.bg,
                        border: `1px solid ${typeStyle.border}`,
                      }}
                    >
                      {anom.anomaly_type}
                    </span>
                    {anom.flight_phase && (
                      <span className="text-[10px] font-mono" style={{ color: 'var(--text-muted)' }}>
                        [{anom.flight_phase}]
                      </span>
                    )}
                  </div>
                  <p className="text-[11px] leading-relaxed" style={{ color: 'var(--text-sub)' }}>
                    {anom.description}
                  </p>
                  {anom.expected_range_min !== undefined && anom.expected_range_min !== null && (
                    <div className="text-[10px] font-mono flex items-center justify-between" style={{ color: 'var(--text-muted)' }}>
                      <span>Bounds: [{anom.expected_range_min}, {anom.expected_range_max}]</span>
                      <span className="text-cyan-400 opacity-0 group-hover:opacity-100 transition-opacity text-[9px] font-bold uppercase">
                        🔍 Click for Deep-Dive →
                      </span>
                    </div>
                  )}
                </div>

                <div className="flex flex-col items-end space-y-1.5 ml-3 flex-shrink-0">
                  <span
                    className="text-[10px] font-bold px-2 py-0.5 rounded-md uppercase font-mono"
                    style={{
                      background: sevStyle.bg,
                      color: sevStyle.color,
                      border: `1px solid ${sevStyle.border}`,
                    }}
                  >
                    {anom.severity}
                  </span>
                  <span className="text-[10px] font-mono" style={{ color: 'var(--text-muted)' }}>
                    Conf: {(anom.confidence * 100).toFixed(0)}%
                  </span>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
