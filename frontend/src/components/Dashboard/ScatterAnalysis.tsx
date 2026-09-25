import React, { useState, useEffect } from 'react';
import { api } from '../../services/api';
import { ScatterChart, Scatter, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Cell } from 'recharts';
import { Grid, RefreshCw, AlertTriangle, Layers, Info } from 'lucide-react';

interface ScatterAnalysisProps {
  onSelectAnomaly?: (anomalyId: number) => void;
}

const PARAM_OPTIONS = [
  { value: 'P_chamber', label: 'P_chamber (MPa)', unit: 'MPa' },
  { value: 'T_chamber', label: 'T_chamber (K)', unit: 'K' },
  { value: 'm_ox', label: 'm_ox (kg/s)', unit: 'kg/s' },
  { value: 'm_fuel', label: 'm_fuel (kg/s)', unit: 'kg/s' },
  { value: 'F_thrust', label: 'F_thrust (kN)', unit: 'kN' },
  { value: 'N_pump', label: 'N_pump (RPM)', unit: 'RPM' },
  { value: 'P_tank_lox', label: 'P_tank_lox (MPa)', unit: 'MPa' },
  { value: 'P_tank_fuel', label: 'P_tank_fuel (MPa)', unit: 'MPa' },
  { value: 'vib_x', label: 'vib_x (g)', unit: 'g' },
  { value: 'acc_axial', label: 'acc_axial (g)', unit: 'g' },
  { value: 'v_batt', label: 'v_batt (V)', unit: 'V' },
  { value: 'i_bus', label: 'i_bus (A)', unit: 'A' },
  { value: 'T_skin', label: 'T_skin (K)', unit: 'K' },
];

const PHASE_COLORS: Record<string, string> = {
  PRE_LAUNCH: '#60a5fa',       // Blue
  LIFTOFF: '#f59e0b',          // Amber
  MAX_Q: '#ec4899',            // Pink
  STAGE_1_FLIGHT: '#10b981',   // Emerald
  STAGE_SEPARATION: '#a855f7', // Purple
  STAGE_2_FLIGHT: '#06b6d4',   // Cyan
  COAST_ORBIT: '#64748b',      // Slate
};

const PHASE_OPTIONS = [
  'ALL',
  'PRE_LAUNCH',
  'LIFTOFF',
  'MAX_Q',
  'STAGE_1_FLIGHT',
  'STAGE_SEPARATION',
  'STAGE_2_FLIGHT',
  'COAST_ORBIT',
];

export const ScatterAnalysis: React.FC<ScatterAnalysisProps> = ({ onSelectAnomaly }) => {
  const [xParam, setXParam] = useState<string>('m_ox');
  const [yParam, setYParam] = useState<string>('F_thrust');
  const [selectedPhase, setSelectedPhase] = useState<string>('ALL');
  const [anomalyFilter, setAnomalyFilter] = useState<string>('ALL');
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState<boolean>(false);

  const fetchScatter = () => {
    setLoading(true);
    api.getScatterData(xParam, yParam, selectedPhase, anomalyFilter)
      .then((res) => {
        setData(res);
        setLoading(false);
      })
      .catch(() => {
        setLoading(false);
      });
  };

  useEffect(() => {
    fetchScatter();
  }, [xParam, yParam, selectedPhase, anomalyFilter]);

  const points = data?.points || [];
  const xUnit = data?.x_unit || PARAM_OPTIONS.find((p) => p.value === xParam)?.unit || '';
  const yUnit = data?.y_unit || PARAM_OPTIONS.find((p) => p.value === yParam)?.unit || '';
  const correlationR = data?.correlation_r;
  const correlationLabel = data?.correlation_label || 'Calculated';

  // Compute tight domain bounds from actual points with 5% padding
  const xVals = points.map((p: any) => p.x);
  const yVals = points.map((p: any) => p.y);
  const minX = xVals.length > 0 ? Math.min(...xVals) : 0;
  const maxX = xVals.length > 0 ? Math.max(...xVals) : 10;
  const minY = yVals.length > 0 ? Math.min(...yVals) : 0;
  const maxY = yVals.length > 0 ? Math.max(...yVals) : 10;

  const padX = (maxX - minX) * 0.05 || 0.5;
  const padY = (maxY - minY) * 0.05 || 0.5;

  const xDomain = [Math.floor((minX - padX) * 10) / 10, Math.ceil((maxX + padX) * 10) / 10];
  const yDomain = [Math.floor((minY - padY) * 10) / 10, Math.ceil((maxY + padY) * 10) / 10];

  const handlePointClick = (pt: any) => {
    if (pt && pt.is_anomalous && pt.anomaly_id && onSelectAnomaly) {
      onSelectAnomaly(pt.anomaly_id);
    }
  };

  return (
    <div className="glass-panel p-3.5 sm:p-4 flex flex-col space-y-3">
      {/* Header & Controls */}
      <div
        className="flex flex-wrap items-center justify-between pb-2.5 gap-2 border-b"
        style={{ borderColor: 'var(--divider)' }}
      >
        <div className="flex items-center space-x-2.5">
          <div
            className="p-2 rounded-xl"
            style={{
              background: 'rgba(6, 182, 212, 0.12)',
              border: '1px solid rgba(6, 182, 212, 0.3)',
            }}
          >
            <Grid className="w-4 h-4 text-cyan-400" />
          </div>
          <div>
            <h2 className="text-sm font-bold uppercase tracking-wider text-slate-100">
              Parametric Correlation Scatter
            </h2>
            <p className="text-[10px] font-mono text-slate-400">
              Real Telemetry Observations & Outlier Correlation
            </p>
          </div>
        </div>

        {/* High Contrast Parameter & Filter Dropdowns */}
        <div className="flex flex-wrap items-center gap-2 text-xs font-mono">
          {/* X Param Select */}
          <div className="flex items-center space-x-1">
            <span className="text-slate-400 font-bold">X:</span>
            <select
              value={xParam}
              onChange={(e) => setXParam(e.target.value)}
              className="bg-slate-900 text-white font-bold text-xs rounded-lg px-2.5 py-1.5 border border-slate-700 focus:outline-none focus:border-cyan-500 shadow-sm"
            >
              {PARAM_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value} className="bg-slate-900 text-white font-mono font-bold">
                  {opt.label}
                </option>
              ))}
            </select>
          </div>

          {/* Y Param Select */}
          <div className="flex items-center space-x-1">
            <span className="text-slate-400 font-bold">Y:</span>
            <select
              value={yParam}
              onChange={(e) => setYParam(e.target.value)}
              className="bg-slate-900 text-white font-bold text-xs rounded-lg px-2.5 py-1.5 border border-slate-700 focus:outline-none focus:border-cyan-500 shadow-sm"
            >
              {PARAM_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value} className="bg-slate-900 text-white font-mono font-bold">
                  {opt.label}
                </option>
              ))}
            </select>
          </div>

          {/* Phase Filter */}
          <div className="flex items-center space-x-1">
            <span className="text-slate-400 font-bold">Phase:</span>
            <select
              value={selectedPhase}
              onChange={(e) => setSelectedPhase(e.target.value)}
              className="bg-slate-900 text-cyan-300 font-bold text-xs rounded-lg px-2 py-1.5 border border-slate-700 focus:outline-none shadow-sm"
            >
              {PHASE_OPTIONS.map((ph) => (
                <option key={ph} value={ph} className="bg-slate-900 text-white font-mono font-bold">
                  {ph}
                </option>
              ))}
            </select>
          </div>

          {/* Anomaly Filter */}
          <div className="flex items-center space-x-1">
            <span className="text-slate-400 font-bold">Points:</span>
            <select
              value={anomalyFilter}
              onChange={(e) => setAnomalyFilter(e.target.value)}
              className="bg-slate-900 text-amber-300 font-bold text-xs rounded-lg px-2 py-1.5 border border-slate-700 focus:outline-none shadow-sm"
            >
              <option value="ALL" className="bg-slate-900 text-white font-mono font-bold">ALL ({data?.total_points || 0})</option>
              <option value="NORMAL" className="bg-slate-900 text-white font-mono font-bold">NOMINAL ONLY</option>
              <option value="ANOMALOUS" className="bg-slate-900 text-white font-mono font-bold">ANOMALIES ONLY ({data?.anomalous_count || 0})</option>
            </select>
          </div>

          <button
            onClick={fetchScatter}
            disabled={loading}
            className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors border border-slate-700"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Statistical Summary & Correlation Indicator */}
      <div className="flex flex-wrap items-center justify-between gap-2 text-[11px] font-mono px-1 bg-slate-900/60 p-2 rounded-xl border border-slate-800">
        <div className="flex items-center space-x-3">
          <div className="flex items-center space-x-1.5">
            <span className="text-slate-400">Correlation:</span>
            <span className="font-bold text-cyan-300">
              {correlationR !== null && correlationR !== undefined ? `r = ${correlationR > 0 ? '+' : ''}${correlationR}` : 'N/A'}
            </span>
            <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-cyan-500/10 border border-cyan-500/30 text-cyan-400">
              {correlationLabel}
            </span>
          </div>

          <div className="hidden sm:flex items-center space-x-1 text-slate-500 text-[10px]">
            <Info className="w-3 h-3 text-slate-400" />
            <span>Co-variation across flight phases (not direct causation)</span>
          </div>
        </div>

        <div className="flex items-center space-x-3 text-[10px]">
          <span className="text-slate-400">
            Observations: <strong className="text-white">{points.length}</strong>
          </span>
          <span className="text-emerald-400">
            Nominal: <strong>{data?.nominal_count || 0}</strong>
          </span>
          <span className="text-rose-400 font-bold">
            Anomalies: <strong>{data?.anomalous_count || 0}</strong>
          </span>
        </div>
      </div>

      {/* Phase Color Legend */}
      <div className="flex flex-wrap items-center justify-between text-[10px] font-mono text-slate-400 px-1 gap-2">
        <div className="flex items-center space-x-3 flex-wrap">
          {Object.entries(PHASE_COLORS).map(([phase, color]) => (
            <div key={phase} className="flex items-center space-x-1">
              <span className="w-2.5 h-2.5 rounded-full shadow-sm" style={{ background: color }} />
              <span className="text-slate-300 font-semibold">{phase}</span>
            </div>
          ))}
        </div>

        <div className="flex items-center space-x-1.5 text-rose-400 font-bold bg-rose-500/10 px-2 py-0.5 rounded border border-rose-500/20">
          <AlertTriangle className="w-3.5 h-3.5 text-rose-400" />
          <span>Red Ring = Anomalous Point (Click to Deep-Dive)</span>
        </div>
      </div>

      {/* True Scatter Plot */}
      <div className="w-full h-[220px] sm:h-[250px]">
        {loading ? (
          <div className="h-full flex items-center justify-center text-slate-400 text-xs font-mono">
            Loading telemetry scatter observations...
          </div>
        ) : points.length === 0 ? (
          <div className="h-full flex items-center justify-center text-slate-500 text-xs font-mono">
            No scatter observations match the selected filters.
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <ScatterChart margin={{ top: 10, right: 15, left: -5, bottom: 15 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255, 255, 255, 0.06)" />
              <XAxis
                type="number"
                dataKey="x"
                name={xParam}
                unit={` ${xUnit}`}
                domain={xDomain}
                allowDataOverflow={true}
                stroke="#64748b"
                tick={{ fontSize: 10, fill: '#94a3b8' }}
                label={{
                  value: `${xParam} (${xUnit})`,
                  position: 'insideBottom',
                  offset: -8,
                  fill: '#94a3b8',
                  fontSize: 10,
                  fontFamily: 'monospace',
                }}
              />
              <YAxis
                type="number"
                dataKey="y"
                name={yParam}
                unit={` ${yUnit}`}
                domain={yDomain}
                allowDataOverflow={true}
                stroke="#64748b"
                tick={{ fontSize: 10, fill: '#94a3b8' }}
                label={{
                  value: `${yParam} (${yUnit})`,
                  angle: -90,
                  position: 'insideLeft',
                  offset: 12,
                  fill: '#94a3b8',
                  fontSize: 10,
                  fontFamily: 'monospace',
                }}
              />
              <Tooltip
                cursor={{ strokeDasharray: '3 3', stroke: 'rgba(255, 255, 255, 0.2)' }}
                content={({ active, payload }) => {
                  if (active && payload && payload.length) {
                    const pt = payload[0].payload;
                    return (
                      <div className="bg-slate-900/95 border border-slate-700 p-3 rounded-xl text-xs font-mono text-white shadow-2xl space-y-1.5 min-w-[180px]">
                        <div className="flex items-center justify-between border-b border-slate-800 pb-1">
                          <span className="font-bold text-amber-400">T+{pt.timestamp}s</span>
                          <span
                            className="text-[9px] px-1.5 py-0.5 rounded font-bold uppercase"
                            style={{
                              background: `${PHASE_COLORS[pt.flight_phase] || '#38bdf8'}25`,
                              color: PHASE_COLORS[pt.flight_phase] || '#38bdf8',
                              border: `1px solid ${PHASE_COLORS[pt.flight_phase] || '#38bdf8'}40`,
                            }}
                          >
                            {pt.flight_phase}
                          </span>
                        </div>

                        <div className="space-y-0.5 text-[11px]">
                          <div>
                            <span className="text-slate-400">{xParam}: </span>
                            <strong className="text-sky-300">{pt.x} {xUnit}</strong>
                          </div>
                          <div>
                            <span className="text-slate-400">{yParam}: </span>
                            <strong className="text-emerald-300">{pt.y} {yUnit}</strong>
                          </div>
                        </div>

                        {pt.is_anomalous ? (
                          <div className="pt-1 border-t border-slate-800 text-rose-400 space-y-0.5">
                            <div className="font-bold text-[10px] uppercase tracking-wider flex items-center justify-between">
                              <span>⚠️ ANOMALY DETECTED</span>
                              {pt.severity && (
                                <span className="px-1.5 py-0.2 rounded bg-rose-500/20 text-rose-300 border border-rose-500/40 text-[9px]">
                                  {pt.severity}
                                </span>
                              )}
                            </div>
                            {pt.anomaly_type && (
                              <div className="text-[10px] text-slate-300 font-semibold">
                                Type: <span className="text-purple-300">{pt.anomaly_type}</span>
                              </div>
                            )}
                            <div className="text-[9px] text-cyan-300 font-bold underline mt-1 cursor-pointer">
                              Click dot to view Deep-Dive →
                            </div>
                          </div>
                        ) : (
                          <div className="pt-1 text-[10px] text-emerald-400 font-semibold">
                            Status: NOMINAL
                          </div>
                        )}
                      </div>
                    );
                  }
                  return null;
                }}
              />
              <Scatter
                name="Telemetry Observations"
                data={points}
                onClick={(node) => handlePointClick(node?.payload)}
              >
                {points.map((entry: any, index: number) => {
                  const baseColor = PHASE_COLORS[entry.flight_phase] || '#38bdf8';
                  return (
                    <Cell
                      key={`scatter-cell-${index}`}
                      fill={entry.is_anomalous ? '#f43f5e' : baseColor}
                      stroke={entry.is_anomalous ? '#ffe4e6' : 'none'}
                      strokeWidth={entry.is_anomalous ? 2.5 : 0}
                      r={entry.is_anomalous ? 6 : 3.5}
                      className={entry.is_anomalous ? 'cursor-pointer hover:scale-125 transition-transform' : 'cursor-pointer'}
                    />
                  );
                })}
              </Scatter>
            </ScatterChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
};
