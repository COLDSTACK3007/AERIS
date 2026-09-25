import React, { useEffect, useState } from 'react';
import { api } from '../../services/api';
import {
  X, AlertTriangle, ShieldCheck, Activity, LineChart as ChartIcon, Layers, FileText, CheckCircle2, AlertOctagon
} from 'lucide-react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine
} from 'recharts';

interface AnomalyDeepDiveProps {
  anomalyId: number | null;
  onClose: () => void;
}

export const AnomalyDeepDive: React.FC<AnomalyDeepDiveProps> = ({ anomalyId, onClose }) => {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!anomalyId) return;
    setLoading(true);
    setError(null);
    api.getAnomalyDeepDive(anomalyId)
      .then((res) => {
        setData(res);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message || 'Failed to load deep-dive analysis.');
        setLoading(false);
      });
  }, [anomalyId]);

  if (!anomalyId) return null;

  const basic = data?.basic_info || {};
  const observed = data?.observed_values || {};
  const timeline = data?.timeline?.data || [];
  const related = data?.related_parameters || [];
  const physics = data?.physics_validation?.checks || [];
  const attribution = data?.attribution || [];
  const explanation = data?.explanation || '';

  const formatTs = (ts: any) => {
    if (ts === undefined || ts === null) return '0.0';
    const num = Number(ts);
    return isNaN(num) ? '0.0' : num.toFixed(1);
  };

  const sevStyle = (severity: string) => {
    switch (severity) {
      case 'CRITICAL':
        return { background: 'rgba(244, 63, 94, 0.15)', color: '#fb7185', border: '1px solid rgba(244, 63, 94, 0.3)' };
      case 'WARNING':
        return { background: 'rgba(245, 158, 11, 0.15)', color: '#fbbf24', border: '1px solid rgba(245, 158, 11, 0.3)' };
      default:
        return { background: 'rgba(59, 130, 246, 0.15)', color: '#60a5fa', border: '1px solid rgba(59, 130, 246, 0.3)' };
    }
  };

  /* ── Shared inline style helpers (theme-aware via CSS vars) ── */
  const cardStyle: React.CSSProperties = {
    background: 'var(--pill-bg)',
    borderColor: 'var(--pill-border)',
  };
  const statBoxStyle: React.CSSProperties = {
    background: 'var(--card-bg-solid)',
    borderColor: 'var(--pill-border)',
  };
  const mainText: React.CSSProperties = { color: 'var(--text-main)' };
  const mutedText: React.CSSProperties = { color: 'var(--text-muted)' };

  return (
    /* ── Overlay: click backdrop to close ── */
    <div
      className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto"
      style={{ background: 'rgba(0,0,0,0.6)', backdropFilter: 'blur(6px)' }}
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      {/* ── Modal Panel ── */}
      <div
        className="relative w-full max-w-3xl my-4 mx-2 sm:mx-auto flex flex-col rounded-xl shadow-2xl border"
        style={{
          background: 'var(--card-bg-solid)',
          borderColor: 'var(--card-border)',
          maxHeight: 'calc(100vh - 2rem)',
        }}
      >
        {/* ── Close Button — always visible, pinned top-right ── */}
        <button
          onClick={onClose}
          className="absolute top-2 right-2 z-10 flex items-center justify-center w-8 h-8 rounded-lg transition-colors"
          style={{
            background: 'var(--pill-bg)',
            border: '1px solid var(--pill-border)',
            color: 'var(--text-muted)',
          }}
          aria-label="Close modal"
        >
          <X className="w-4 h-4" />
        </button>

        {/* ── Header ── */}
        <div
          className="flex items-center gap-2.5 px-3 py-2.5 sm:px-4 sm:py-3 border-b flex-shrink-0"
          style={{ borderColor: 'var(--divider)' }}
        >
          <div
            className="p-1.5 rounded-lg flex-shrink-0"
            style={{
              background: 'rgba(245, 158, 11, 0.15)',
              border: '1px solid rgba(245, 158, 11, 0.3)',
            }}
          >
            <AlertTriangle className="w-4 h-4" style={{ color: '#f59e0b' }} />
          </div>
          <div className="min-w-0 pr-8">
            <div className="flex flex-wrap items-center gap-1.5">
              <h2 className="text-sm font-bold tracking-wide truncate" style={mainText}>
                Anomaly Deep-Dive — {basic.parameter || 'Investigation'}
              </h2>
              {basic.severity && (
                <span
                  className="text-[9px] font-mono font-bold px-1.5 py-px rounded uppercase whitespace-nowrap"
                  style={sevStyle(basic.severity)}
                >
                  {basic.severity}
                </span>
              )}
              {basic.anomaly_type && (
                <span
                  className="text-[9px] font-mono font-bold px-1.5 py-px rounded uppercase whitespace-nowrap"
                  style={{ background: 'rgba(139, 92, 246, 0.15)', color: '#c084fc', border: '1px solid rgba(139, 92, 246, 0.3)' }}
                >
                  {basic.anomaly_type}
                </span>
              )}
            </div>
            <p className="text-[10px] font-mono mt-0.5" style={mutedText}>
              Subsystem: <span style={{ color: 'var(--accent-cyan)', fontWeight: 600 }}>{basic.subsystem || 'N/A'}</span>{' '}
              | T+{formatTs(basic.timestamp)}s | Phase:{' '}
              <span style={{ color: '#f59e0b', fontWeight: 600 }}>{basic.flight_phase || 'N/A'}</span>
            </p>
          </div>
        </div>

        {/* ── Body (scrollable) ── */}
        <div className="flex-1 overflow-y-auto px-3 py-3 sm:px-4 sm:py-4 space-y-3 text-xs">
          {loading ? (
            <div className="flex flex-col items-center justify-center py-12 space-y-2" style={mutedText}>
              <Activity className="w-6 h-6 animate-spin" style={{ color: '#f59e0b' }} />
              <p className="font-mono text-[11px]">Calculating residuals & reconstructing trajectory…</p>
            </div>
          ) : error ? (
            <div
              className="p-3 rounded-lg flex items-center gap-2 font-mono text-[11px]"
              style={{ background: 'rgba(244,63,94,0.1)', border: '1px solid rgba(244,63,94,0.3)', color: '#fb7185' }}
            >
              <AlertOctagon className="w-4 h-4 flex-shrink-0" />
              <span>{error}</span>
            </div>
          ) : (
            <>
              {/* ── Diagnosis ── */}
              {explanation && (
                <div
                  className="p-3 rounded-lg border flex items-start gap-2.5"
                  style={{ ...cardStyle, borderColor: 'rgba(6, 182, 212, 0.25)' }}
                >
                  <FileText className="w-4 h-4 flex-shrink-0 mt-0.5" style={{ color: 'var(--accent-cyan)' }} />
                  <div className="min-w-0">
                    <h3
                      className="font-bold uppercase tracking-wider mb-0.5 text-[10px]"
                      style={{ color: 'var(--accent-cyan)' }}
                    >
                      Calculated Diagnosis & Evidence
                    </h3>
                    <p className="leading-relaxed text-[11px]" style={mainText}>{explanation}</p>
                  </div>
                </div>
              )}

              {/* ── Observed vs Expected + Attribution ── */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {/* Observed Card */}
                <div className="p-3 rounded-lg border space-y-2" style={cardStyle}>
                  <div className="flex items-center gap-1.5 font-bold uppercase tracking-wider text-[10px]" style={{ color: '#f59e0b' }}>
                    <ShieldCheck className="w-3.5 h-3.5" />
                    <span>Observed vs Phase Bounds</span>
                  </div>
                  <div className="grid grid-cols-2 gap-2 font-mono text-[11px]">
                    {/* Observed Value */}
                    <div className="p-2 rounded-md border" style={statBoxStyle}>
                      <span className="text-[9px] uppercase block font-semibold" style={mutedText}>Observed</span>
                      <span className="text-sm font-bold" style={{ color: 'var(--accent-cyan)' }}>
                        {observed.observed_value ?? 'N/A'}{' '}
                        <span className="text-[10px] font-normal" style={mutedText}>{observed.unit}</span>
                      </span>
                    </div>
                    {/* Z-score */}
                    <div className="p-2 rounded-md border" style={statBoxStyle}>
                      <span className="text-[9px] uppercase block font-semibold" style={mutedText}>Phase z-score</span>
                      <span className="text-sm font-bold" style={{ color: '#f59e0b' }}>
                        {observed.phase_z_score !== undefined ? `${observed.phase_z_score.toFixed(2)}σ` : 'N/A'}
                      </span>
                    </div>
                    {/* Expected Range */}
                    <div className="p-2 rounded-md border" style={statBoxStyle}>
                      <span className="text-[9px] uppercase block font-semibold" style={mutedText}>Expected Range</span>
                      <span className="text-xs font-semibold" style={{ color: 'var(--accent-emerald)' }}>
                        [{observed.phase_expected_min ?? '—'}, {observed.phase_expected_max ?? '—'}]
                      </span>
                    </div>
                    {/* Safe Bounds */}
                    <div className="p-2 rounded-md border" style={statBoxStyle}>
                      <span className="text-[9px] uppercase block font-semibold" style={mutedText}>Safe Bounds</span>
                      <span className="text-xs font-semibold" style={{ color: 'var(--accent-violet)' }}>
                        [{observed.absolute_min ?? '—'}, {observed.absolute_max ?? '—'}]
                      </span>
                    </div>
                  </div>
                </div>

                {/* Attribution Card */}
                <div className="p-3 rounded-lg border space-y-2 flex flex-col" style={cardStyle}>
                  <div className="flex items-center gap-1.5 font-bold uppercase tracking-wider text-[10px]" style={{ color: 'var(--accent-cyan)' }}>
                    <Layers className="w-3.5 h-3.5" />
                    <span>Contributing Anomaly Signals</span>
                  </div>
                  <div className="space-y-2 flex-1 flex flex-col justify-center">
                    {attribution.length === 0 ? (
                      <p className="italic text-[11px]" style={mutedText}>No attribution factors recorded.</p>
                    ) : (
                      attribution.map((item: any, idx: number) => {
                        const pct = Math.round((item.normalized_score || 0) * 100);
                        return (
                          <div key={idx} className="space-y-0.5">
                            <div className="flex justify-between font-mono text-[10px]">
                              <span className="font-semibold" style={mainText}>{item.factor}</span>
                              <span className="font-semibold" style={{ color: '#f59e0b' }}>{item.description}</span>
                            </div>
                            <div
                              className="w-full h-1.5 rounded-full overflow-hidden"
                              style={{ background: 'var(--card-bg-solid)', border: '1px solid var(--pill-border)' }}
                            >
                              <div
                                className="h-full rounded-full"
                                style={{
                                  width: `${Math.min(100, Math.max(8, pct))}%`,
                                  background:
                                    pct > 75
                                      ? 'linear-gradient(90deg, #f43f5e, #fb7185)'
                                      : pct > 40
                                      ? 'linear-gradient(90deg, #f59e0b, #fbbf24)'
                                      : 'linear-gradient(90deg, #06b6d4, #38bdf8)',
                                }}
                              />
                            </div>
                          </div>
                        );
                      })
                    )}
                  </div>
                </div>
              </div>

              {/* ── Timeline Chart ── */}
              <div className="p-3 rounded-lg border space-y-2" style={cardStyle}>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1.5 font-bold uppercase tracking-wider text-[10px]" style={{ color: 'var(--accent-cyan)' }}>
                    <ChartIcon className="w-3.5 h-3.5" />
                    <span>Trajectory Timeline (±15s)</span>
                  </div>
                  <span className="text-[9px] font-mono" style={mutedText}>
                    Param: <span style={{ color: '#f59e0b', fontWeight: 700 }}>{basic.parameter}</span>
                  </span>
                </div>
                <div className="h-44 sm:h-52 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={timeline} margin={{ top: 8, right: 12, left: -22, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="var(--grid-line)" />
                      <XAxis
                        dataKey="timestamp"
                        stroke="var(--text-muted)"
                        tick={{ fontSize: 9, fill: 'var(--text-muted)' }}
                        tickFormatter={(v) => `${v}s`}
                      />
                      <YAxis stroke="var(--text-muted)" tick={{ fontSize: 9, fill: 'var(--text-muted)' }} />
                      <Tooltip
                        contentStyle={{
                          background: 'var(--card-bg-solid)',
                          border: '1px solid var(--card-border)',
                          borderRadius: '6px',
                          color: 'var(--text-main)',
                          fontSize: '10px',
                          boxShadow: 'var(--card-shadow)',
                        }}
                      />
                      {observed.phase_expected_min !== undefined && (
                        <ReferenceLine
                          y={observed.phase_expected_min}
                          stroke="#10b981"
                          strokeDasharray="4 4"
                          label={{ value: 'Min', fill: '#10b981', fontSize: 8, position: 'insideBottomRight' }}
                        />
                      )}
                      {observed.phase_expected_max !== undefined && (
                        <ReferenceLine
                          y={observed.phase_expected_max}
                          stroke="#10b981"
                          strokeDasharray="4 4"
                          label={{ value: 'Max', fill: '#10b981', fontSize: 8, position: 'insideTopRight' }}
                        />
                      )}
                      {basic.timestamp !== undefined && (
                        <ReferenceLine
                          x={Number(basic.timestamp)}
                          stroke="#f43f5e"
                          strokeWidth={2}
                          label={{ value: '▼ Anomaly', fill: '#f43f5e', fontSize: 9, position: 'top' }}
                        />
                      )}
                      <Line
                        type="monotone"
                        dataKey="value"
                        stroke="var(--accent-cyan)"
                        strokeWidth={2}
                        dot={false}
                        activeDot={{ r: 4, fill: '#f59e0b' }}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* ── Related Telemetry + Physics Checks ── */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {/* Related Telemetry */}
                <div className="p-3 rounded-lg border space-y-2" style={cardStyle}>
                  <h4 className="font-bold uppercase tracking-wider text-[10px]" style={{ color: 'var(--accent-violet)' }}>
                    Related Telemetry at T+{formatTs(basic.timestamp)}s
                  </h4>
                  {related.length === 0 ? (
                    <p className="italic text-[11px]" style={mutedText}>No related telemetry.</p>
                  ) : (
                    <div className="overflow-x-auto">
                      <table className="w-full text-left font-mono text-[10px]">
                        <thead>
                          <tr style={{ borderBottom: '1px solid var(--divider)', ...mutedText }}>
                            <th className="pb-1 font-semibold">Param</th>
                            <th className="pb-1 font-semibold">Value</th>
                            <th className="pb-1 font-semibold">Nominal</th>
                            <th className="pb-1 font-semibold">Dev</th>
                          </tr>
                        </thead>
                        <tbody>
                          {related.map((r: any, idx: number) => (
                            <tr
                              key={idx}
                              style={{ borderBottom: '1px solid var(--divider)' }}
                            >
                              <td className="py-1 font-bold" style={mainText}>{r.parameter}</td>
                              <td className="py-1 font-semibold" style={{ color: 'var(--accent-cyan)' }}>
                                {r.value}{' '}
                                <span className="text-[8px]" style={mutedText}>{r.unit}</span>
                              </td>
                              <td className="py-1" style={mutedText}>{r.nominal ?? 'N/A'}</td>
                              <td
                                className="py-1 font-semibold"
                                style={{
                                  color:
                                    r.deviation_from_nominal && Math.abs(r.deviation_from_nominal) > 1.0
                                      ? '#f59e0b'
                                      : 'var(--accent-emerald)',
                                }}
                              >
                                {r.deviation_from_nominal !== null && r.deviation_from_nominal !== undefined
                                  ? (r.deviation_from_nominal > 0 ? `+${r.deviation_from_nominal}` : r.deviation_from_nominal)
                                  : 'N/A'}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>

                {/* Physics Checks */}
                <div className="p-3 rounded-lg border space-y-2" style={cardStyle}>
                  <h4 className="font-bold uppercase tracking-wider text-[10px]" style={{ color: 'var(--accent-emerald)' }}>
                    Physics Equation Checks
                  </h4>
                  {physics.length === 0 ? (
                    <p className="italic text-[11px]" style={mutedText}>No physics violations.</p>
                  ) : (
                    <div className="space-y-2">
                      {physics.map((chk: any, idx: number) => (
                        <div
                          key={idx}
                          className="p-2 rounded-md border space-y-1 font-mono"
                          style={statBoxStyle}
                        >
                          <div className="flex items-center justify-between text-[10px]">
                            <span className="font-bold" style={mainText}>{chk.relationship}</span>
                            <span
                              className="px-1.5 py-px rounded text-[9px] font-bold uppercase"
                              style={
                                chk.status === 'consistent'
                                  ? { background: 'rgba(16,185,129,0.15)', color: 'var(--accent-emerald)', border: '1px solid rgba(16,185,129,0.3)' }
                                  : { background: 'rgba(244,63,94,0.15)', color: 'var(--accent-rose)', border: '1px solid rgba(244,63,94,0.3)' }
                              }
                            >
                              {chk.status}
                            </span>
                          </div>
                          <div className="flex flex-wrap items-center gap-x-3 text-[9px]" style={mutedText}>
                            <span>Obs: <strong style={mainText}>{chk.observed} {chk.unit}</strong></span>
                            <span>Exp: <strong style={mainText}>{chk.expected} {chk.unit}</strong></span>
                            <span style={{ color: '#f59e0b', fontWeight: 600 }}>Res: {chk.residual} {chk.unit}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
};
