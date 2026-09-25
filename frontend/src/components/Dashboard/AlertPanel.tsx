import React, { useState } from 'react';
import { AlertItem } from '../../types/telemetry';
import { api } from '../../services/api';
import { Bell, AlertOctagon, AlertTriangle, Info, CheckCircle2, ShieldAlert } from 'lucide-react';

interface AlertPanelProps {
  alerts: AlertItem[];
  onSelectAnomaly?: (id: number) => void;
}

export const AlertPanel: React.FC<AlertPanelProps> = ({ alerts, onSelectAnomaly }) => {
  const [filterLevel, setFilterLevel] = useState<string>('ALL');
  const [acknowledgedMap, setAcknowledgedMap] = useState<Record<number, boolean>>({});

  const counts = {
    ALL: alerts.length,
    CRITICAL: alerts.filter((a) => a.level === 'CRITICAL').length,
    WARNING: alerts.filter((a) => a.level === 'WARNING').length,
    INFO: alerts.filter((a) => a.level === 'INFO').length,
  };

  const filteredAlerts = alerts.filter(
    (a) => filterLevel === 'ALL' || a.level === filterLevel
  );

  const handleAcknowledge = async (e: React.MouseEvent, alertId?: number) => {
    e.stopPropagation();
    if (!alertId) return;
    setAcknowledgedMap((prev) => ({ ...prev, [alertId]: true }));
    try {
      await api.acknowledgeAlert(alertId);
    } catch (err) {
      console.error('Failed to acknowledge alert:', err);
    }
  };

  const getAlertIcon = (level: string) => {
    switch (level) {
      case 'CRITICAL':
        return <AlertOctagon className="w-4 h-4 flex-shrink-0 text-rose-400" />;
      case 'WARNING':
        return <AlertTriangle className="w-4 h-4 flex-shrink-0 text-amber-400" />;
      default:
        return <Info className="w-4 h-4 flex-shrink-0 text-sky-400" />;
    }
  };

  const getLevelStyle = (level: string) => {
    switch (level) {
      case 'CRITICAL':
        return { bg: 'rgba(244, 63, 94, 0.08)', border: 'rgba(244, 63, 94, 0.25)', tagColor: '#fb7185' };
      case 'WARNING':
        return { bg: 'rgba(245, 158, 11, 0.08)', border: 'rgba(245, 158, 11, 0.25)', tagColor: '#fbbf24' };
      default:
        return { bg: 'rgba(59, 130, 246, 0.08)', border: 'rgba(59, 130, 246, 0.25)', tagColor: '#60a5fa' };
    }
  };

  return (
    <div className="glass-panel p-4 sm:p-5 flex flex-col h-[320px]">
      {/* Header */}
      <div
        className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5 mb-3 pb-2.5"
        style={{ borderBottom: '1px solid var(--divider)' }}
      >
        <div className="flex items-center space-x-2.5">
          <div
            className="p-2 rounded-xl"
            style={{
              background: 'rgba(244, 63, 94, 0.1)',
              border: '1px solid rgba(244, 63, 94, 0.25)',
            }}
          >
            <Bell className="w-4 h-4 text-rose-400" />
          </div>
          <div>
            <h2 className="text-xs sm:text-sm font-bold tracking-wide uppercase font-mono" style={{ color: 'var(--text-main)' }}>
              Priority Alerts ({alerts.length})
            </h2>
            <p className="text-[10px] font-mono text-slate-400">
              Live Surveillance & Incident Events
            </p>
          </div>
        </div>

        {/* Filter Tabs */}
        <div className="flex items-center space-x-1 overflow-x-auto pb-1 sm:pb-0 font-mono">
          {(['ALL', 'CRITICAL', 'WARNING', 'INFO'] as const).map((level) => {
            const count = counts[level];
            const isSelected = filterLevel === level;
            return (
              <button
                key={level}
                onClick={() => setFilterLevel(level)}
                className="text-[10px] px-2.5 py-1 rounded-lg transition-all font-bold whitespace-nowrap flex items-center space-x-1"
                style={{
                  background: isSelected ? 'rgba(244, 63, 94, 0.12)' : 'var(--pill-bg)',
                  color: isSelected ? '#fb7185' : 'var(--text-muted)',
                  border: `1px solid ${isSelected ? 'rgba(244, 63, 94, 0.3)' : 'var(--pill-border)'}`,
                }}
              >
                <span>{level}</span>
                <span className="opacity-75">({count})</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Alert List */}
      <div className="flex-1 overflow-y-auto space-y-2 pr-1 font-mono">
        {filteredAlerts.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-xs text-slate-400 space-y-2">
            <ShieldAlert className="w-8 h-8 opacity-30 text-emerald-400" />
            <p>No active priority alerts recorded.</p>
          </div>
        ) : (
          filteredAlerts.map((alert, i) => {
            const levelStyle = getLevelStyle(alert.level);
            const isAck = alert.id ? (acknowledgedMap[alert.id] || alert.is_acknowledged) : alert.is_acknowledged;
            return (
              <div
                key={alert.id || i}
                onClick={() => alert.id && onSelectAnomaly && onSelectAnomaly(alert.id)}
                className={`p-3 rounded-xl flex items-start space-x-3 text-xs transition-all ${
                  onSelectAnomaly && alert.id ? 'cursor-pointer hover:border-rose-400/50' : ''
                } ${isAck ? 'opacity-60' : ''}`}
                style={{
                  background: levelStyle.bg,
                  border: `1px solid ${levelStyle.border}`,
                }}
              >
                <div className="mt-0.5">{getAlertIcon(alert.level)}</div>

                <div className="flex-1 space-y-1">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-slate-100 text-xs line-clamp-1">
                      {alert.title}
                    </span>
                    <span className="text-[10px] text-amber-400 font-bold ml-2 whitespace-nowrap">
                      T+{alert.timestamp.toFixed(1)}s
                    </span>
                  </div>

                  <p className="text-[11px] text-slate-300 leading-tight">
                    {alert.message}
                  </p>

                  <div className="flex items-center justify-between pt-1 text-[10px]">
                    <span className="font-bold uppercase tracking-wider" style={{ color: levelStyle.tagColor }}>
                      ● {alert.level} {alert.parameter ? `[${alert.parameter}]` : ''}
                    </span>

                    <button
                      onClick={(e) => handleAcknowledge(e, alert.id)}
                      className={`flex items-center space-x-1 px-2 py-0.5 rounded text-[9px] font-bold transition-colors ${
                        isAck
                          ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30'
                          : 'bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700'
                      }`}
                      title={isAck ? 'Alert Acknowledged' : 'Click to Acknowledge Alert'}
                    >
                      <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                      <span>{isAck ? 'ACKNOWLEDGED' : 'ACK'}</span>
                    </button>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};

