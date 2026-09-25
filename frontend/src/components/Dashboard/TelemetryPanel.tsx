import React, { useState } from 'react';
import { TelemetryDataPoint } from '../../types/telemetry';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Legend,
} from 'recharts';
import { Activity, Layers } from 'lucide-react';

interface TelemetryPanelProps {
  data: TelemetryDataPoint[];
}

export const TelemetryPanel: React.FC<TelemetryPanelProps> = ({ data }) => {
  const [selectedParams, setSelectedParams] = useState<string[]>([
    'F_thrust',
    'P_chamber',
    'm_ox',
    'acc_axial',
  ]);

  const paramMetadata: Record<string, { name: string; unit: string; color: string }> = {
    F_thrust: { name: 'Thrust', unit: 'kN', color: '#f97316' },
    P_chamber: { name: 'Chamber Press', unit: 'MPa', color: '#0891b2' },
    m_ox: { name: 'Oxidizer Flow', unit: 'kg/s', color: '#2563eb' },
    m_fuel: { name: 'Fuel Flow', unit: 'kg/s', color: '#9333ea' },
    N_pump: { name: 'Pump Speed', unit: 'RPM', color: '#db2777' },
    acc_axial: { name: 'Axial Accel', unit: 'g', color: '#059669' },
    T_chamber: { name: 'Chamber Temp', unit: 'K', color: '#e11d48' },
    v_batt: { name: 'Battery Volt', unit: 'V', color: '#d97706' },
  };

  const toggleParam = (param: string) => {
    setSelectedParams((prev) =>
      prev.includes(param) ? prev.filter((p) => p !== param) : [...prev, param]
    );
  };

  const latestPoint = data.length > 0 ? data[data.length - 1] : null;

  return (
    <div className="glass-panel p-3 sm:p-4 flex flex-col h-[290px] sm:h-[340px]">
      {/* Header */}
      <div
        className="flex flex-wrap items-center justify-between mb-3 pb-2.5 gap-2"
        style={{ borderBottom: '1px solid var(--divider)' }}
      >
        <div className="flex items-center space-x-2.5">
          <div
            className="p-1.5 sm:p-2 rounded-xl"
            style={{
              background: 'rgba(249, 115, 22, 0.08)',
              border: '1px solid rgba(249, 115, 22, 0.2)',
            }}
          >
            <Activity className="w-3.5 h-3.5 sm:w-4 sm:h-4" style={{ color: 'var(--isro-orange)' }} />
          </div>
          <div>
            <h2 className="text-xs sm:text-sm font-bold uppercase tracking-wider" style={{ color: 'var(--text-main)' }}>
              Real-Time Telemetry Feed
            </h2>
            <p className="text-[9px] sm:text-[10px] font-mono" style={{ color: 'var(--text-muted)' }}>
              16 Multi-Rate ISRO Sensor Channels
            </p>
          </div>
        </div>

        {/* Parameter Selector Pills */}
        <div className="flex items-center gap-1.5 overflow-x-auto w-full sm:w-auto pb-1 sm:pb-0">
          {Object.keys(paramMetadata).map((param) => {
            const isSelected = selectedParams.includes(param);
            const meta = paramMetadata[param];
            return (
              <button
                key={param}
                onClick={() => toggleParam(param)}
                className="text-[10px] sm:text-[11px] font-mono px-2 sm:px-2.5 py-1 rounded-lg transition-all font-bold flex items-center space-x-1.5 flex-shrink-0"
                style={{
                  background: isSelected ? 'var(--pill-bg)' : 'transparent',
                  color: isSelected ? 'var(--text-main)' : 'var(--text-muted)',
                  border: `1px solid ${isSelected ? meta.color + '60' : 'var(--pill-border)'}`,
                  opacity: isSelected ? 1 : 0.55,
                }}
              >
                <span className="w-1.5 h-1.5 sm:w-2 sm:h-2 rounded-full" style={{ backgroundColor: meta.color }} />
                <span>{param}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Metrics Strip */}
      {latestPoint && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-1.5 sm:gap-2 mb-2 sm:mb-3">
          {selectedParams.map((param) => {
            const meta = paramMetadata[param] || { name: param, unit: '', color: '#0284c7' };
            const rawVal = (latestPoint as any)[param];
            const valStr = rawVal !== undefined && rawVal !== null ? Number(rawVal).toFixed(1) : '—';
            return (
              <div
                key={param}
                className="px-3 py-2 rounded-xl flex items-center justify-between"
                style={{
                  background: 'var(--pill-bg)',
                  border: '1px solid var(--pill-border)',
                }}
              >
                <span className="text-[10px] font-mono uppercase font-bold" style={{ color: 'var(--text-muted)' }}>
                  {meta.name}
                </span>
                <span className="text-xs font-mono font-bold" style={{ color: meta.color }}>
                  {valStr}{' '}
                  <span className="text-[9px] font-normal" style={{ color: 'var(--text-muted)' }}>
                    {meta.unit}
                  </span>
                </span>
              </div>
            );
          })}
        </div>
      )}

      {/* Chart */}
      <div className="flex-1 w-full min-h-0">
        {data.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-xs" style={{ color: 'var(--text-muted)' }}>
            <Layers className="w-8 h-8 mb-2 animate-pulse" style={{ color: 'var(--text-muted)' }} />
            <span>No Telemetry Data. Click "Simulate 600s Mission" or Upload CSV.</span>
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data} margin={{ top: 10, right: 15, left: -10, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--grid-line)" />
              <XAxis
                dataKey="timestamp"
                tickFormatter={(val) => `T+${val.toFixed(0)}s`}
                stroke="var(--text-muted)"
                tick={{ fontSize: 10, fill: 'var(--text-muted)' }}
              />
              <YAxis stroke="var(--text-muted)" tick={{ fontSize: 10, fill: 'var(--text-muted)' }} />
              <Tooltip
                contentStyle={{
                  backgroundColor: 'var(--tooltip-bg)',
                  borderColor: 'var(--card-border)',
                  borderRadius: '12px',
                  fontSize: '11px',
                  boxShadow: '0 10px 40px rgba(0,0,0,0.2)',
                  color: 'var(--text-main)',
                  backdropFilter: 'blur(12px)',
                }}
                labelFormatter={(val) => `Mission Elapsed: T+${Number(val).toFixed(1)}s`}
              />
              <Legend wrapperStyle={{ fontSize: '10px', paddingTop: '4px' }} />
              {selectedParams.map((param) => {
                const meta = paramMetadata[param] || { color: '#0284c7' };
                return (
                  <Line
                    key={param}
                    type="monotone"
                    dataKey={param}
                    stroke={meta.color}
                    dot={false}
                    strokeWidth={2}
                    isAnimationActive={false}
                  />
                );
              })}
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
};
