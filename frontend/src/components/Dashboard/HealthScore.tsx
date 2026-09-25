import React from 'react';
import { SystemHealthInfo } from '../../types/telemetry';
import { ShieldCheck } from 'lucide-react';

interface HealthScoreProps {
  healthInfo: SystemHealthInfo | null;
}

export const HealthScore: React.FC<HealthScoreProps> = ({ healthInfo }) => {
  const score = healthInfo?.score ?? 100.0;
  const status = healthInfo?.status ?? 'NOMINAL';
  const summary = healthInfo?.anomalies_summary ?? { critical: 0, warning: 0, info: 0 };

  const backendSubsystems = healthInfo?.subsystem_health;

  const defaultSubsystems = [
    { name: 'PROPULSION', key: 'PROPULSION' },
    { name: 'THERMAL', key: 'THERMAL' },
    { name: 'POWER / ELECT', key: 'POWER / ELECT' },
    { name: 'GUIDANCE / NAV', key: 'GUIDANCE / NAV' },
  ];

  const subsystems = defaultSubsystems.map((subDef) => {
    const subData = backendSubsystems?.[subDef.key];
    if (subData && subData.has_data && subData.score !== null) {
      return {
        name: subDef.name,
        score: subData.score,
        status: subData.status,
        hasData: true,
      };
    } else {
      return {
        name: subDef.name,
        score: null,
        status: subData?.status || 'INSUFFICIENT DATA',
        hasData: false,
      };
    }
  });

  const getStatusBadge = (st: string) => {
    switch (st) {
      case 'NOMINAL':
        return {
          label: 'NOMINAL',
          color: '#10b981',
          bg: 'rgba(16, 185, 129, 0.12)',
          border: 'rgba(16, 185, 129, 0.25)',
          dotBg: '#10b981',
        };
      case 'ATTENTION_REQUIRED':
      case 'WARNING':
        return {
          label: 'WARNING',
          color: '#f59e0b',
          bg: 'rgba(245, 158, 11, 0.12)',
          border: 'rgba(245, 158, 11, 0.25)',
          dotBg: '#f59e0b',
        };
      case 'INSUFFICIENT_DATA':
      case 'INSUFFICIENT DATA':
        return {
          label: 'INSUFFICIENT DATA',
          color: '#94a3b8',
          bg: 'rgba(148, 163, 184, 0.12)',
          border: 'rgba(148, 163, 184, 0.25)',
          dotBg: '#94a3b8',
        };
      default:
        return {
          label: 'CRITICAL',
          color: '#f43f5e',
          bg: 'rgba(244, 63, 94, 0.12)',
          border: 'rgba(244, 63, 94, 0.25)',
          dotBg: '#f43f5e',
        };
    }
  };


  const statusBadge = getStatusBadge(status);

  // Explanation line if backend data supports it
  const getExplanation = () => {
    if (summary.critical > 0) {
      return `${summary.critical} critical event${summary.critical > 1 ? 's' : ''} detected`;
    }
    if (summary.warning > 0) {
      return `${summary.warning} warning event${summary.warning > 1 ? 's' : ''} detected`;
    }
    return null;
  };

  const explanation = getExplanation();

  return (
    <div className="glass-panel p-4 sm:p-5 flex flex-col justify-between space-y-4 h-full">
      {/* 1. HEADER */}
      <div className="flex items-center justify-between pb-3 border-b" style={{ borderColor: 'var(--divider)' }}>
        <div className="flex items-center space-x-2">
          <ShieldCheck className="w-4 h-4 text-cyan-400" />
          <h2 className="text-xs font-bold uppercase tracking-wider text-slate-100 font-mono">
            System Health Index
          </h2>
        </div>
        <div className="flex items-center space-x-1.5 text-[10px] font-mono text-slate-400">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
          <span className="font-semibold tracking-wider text-slate-300">MONITORING</span>
        </div>
      </div>

      {/* 2. OVERALL HEALTH SECTION */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-[11px] font-mono uppercase tracking-wider text-slate-400">
            Overall Health
          </span>
          <div
            className="px-2.5 py-0.5 rounded text-[11px] font-mono font-bold flex items-center space-x-1.5"
            style={{
              background: statusBadge.bg,
              color: statusBadge.color,
              border: `1px solid ${statusBadge.border}`,
            }}
          >
            <span
              className="w-1.5 h-1.5 rounded-full"
              style={{ background: statusBadge.dotBg }}
            />
            <span>{statusBadge.label}</span>
          </div>
        </div>

        <div className="flex items-baseline space-x-2 font-mono">
          <span className="text-3xl font-bold tracking-tight text-white">
            {score.toFixed(0)}%
          </span>
          {explanation && (
            <span className="text-[11px] text-slate-400 font-medium">
              ({explanation})
            </span>
          )}
        </div>

        {/* 6px thin horizontal meter */}
        <div className="w-full h-[6px] rounded-full bg-slate-800/80 overflow-hidden">
          <div
            className="h-full rounded-full transition-all duration-700"
            style={{
              width: `${Math.min(100, Math.max(0, score))}%`,
              background: statusBadge.color,
            }}
          />
        </div>
      </div>

      {/* 3. SUBSYSTEM SECTION */}
      <div className="space-y-3 pt-1">
        <div className="text-[11px] font-mono uppercase tracking-wider text-slate-400">
          Subsystem Health
        </div>

        <div className="space-y-2.5">
          {subsystems.map((sub, idx) => {
            const subBadge = getStatusBadge(sub.status);
            return (
              <div key={idx} className="space-y-1">
                <div className="flex items-center justify-between text-[11px] font-mono">
                  <span className="font-semibold text-slate-300">{sub.name}</span>
                  <div className="flex items-center space-x-3">
                    <span className="font-bold text-slate-200">
                      {sub.score !== null ? `${sub.score.toFixed(0)}%` : 'N/A'}
                    </span>
                    <div className="flex items-center space-x-1 text-[10px] font-bold" style={{ color: subBadge.color }}>
                      <span className="w-1.5 h-1.5 rounded-full" style={{ background: subBadge.dotBg }} />
                      <span>{subBadge.label}</span>
                    </div>
                  </div>
                </div>

                {/* 3px thin bar */}
                <div className="w-full h-[3px] rounded-full bg-slate-800/80 overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all duration-500"
                    style={{
                      width: sub.score !== null ? `${sub.score}%` : '0%',
                      background: subBadge.color,
                    }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* 4. ALERT SUMMARY */}
      <div className="pt-3 border-t flex items-center justify-between text-[11px] font-mono" style={{ borderColor: 'var(--divider)' }}>
        <div className="flex items-center space-x-1.5 text-rose-400">
          <span className="w-2 h-2 rounded-full bg-rose-500" />
          <span className="font-bold text-xs">{summary.critical}</span>
          <span className="text-[10px] text-slate-400 uppercase font-semibold">CRITICAL</span>
        </div>
        <div className="flex items-center space-x-1.5 text-amber-400">
          <span className="w-2 h-2 rounded-full bg-amber-500" />
          <span className="font-bold text-xs">{summary.warning}</span>
          <span className="text-[10px] text-slate-400 uppercase font-semibold">WARNING</span>
        </div>
        <div className="flex items-center space-x-1.5 text-cyan-400">
          <span className="w-2 h-2 rounded-full bg-cyan-500" />
          <span className="font-bold text-xs">{summary.info}</span>
          <span className="text-[10px] text-slate-400 uppercase font-semibold">INFO</span>
        </div>
      </div>
    </div>
  );
};

