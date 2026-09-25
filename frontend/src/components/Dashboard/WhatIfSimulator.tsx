import React, { useState } from 'react';
import { api } from '../../services/api';
import { Sliders, Play, AlertTriangle, ShieldCheck, CheckCircle2, ArrowRight } from 'lucide-react';

const PARAM_OPTIONS = [
  { value: 'm_ox', label: 'm_ox (LOX Mass Flow)' },
  { value: 'm_fuel', label: 'm_fuel (RP-1 Mass Flow)' },
  { value: 'P_chamber', label: 'P_chamber (Chamber Pressure)' },
  { value: 'F_thrust', label: 'F_thrust (Rocket Thrust)' },
];

export const WhatIfSimulator: React.FC = () => {
  const [param, setParam] = useState<string>('m_ox');
  const [pct, setPct] = useState<number>(-5.0);
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState<boolean>(false);

  const handleSimulate = () => {
    setLoading(true);
    api.runWhatIf(param, pct)
      .then((res) => {
        setResult(res);
        setLoading(false);
      })
      .catch(() => {
        setLoading(false);
      });
  };

  const downstream = result?.downstream_effects || [];
  const health = result?.health_impact || {};
  const physics = result?.physics_consistency || {};

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
              background: 'rgba(59, 130, 246, 0.08)',
              border: '1px solid rgba(59, 130, 246, 0.2)',
            }}
          >
            <Sliders className="w-4 h-4 text-blue-400" />
          </div>
          <div>
            <h2 className="text-sm font-bold uppercase tracking-wider" style={{ color: 'var(--text-main)' }}>
              Mission What-If Simulator
            </h2>
            <p className="text-[10px] font-mono text-cyan-400">
              PHYSICS-DRIVEN SCENARIO SIMULATION (NON-DESTRUCTIVE)
            </p>
          </div>
        </div>

        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-amber-500/10 border border-amber-500/30 text-amber-300 font-bold uppercase">
          SIMULATION
        </span>
      </div>

      {/* Control Bar */}
      <div className="flex items-center space-x-3 text-xs mb-3 bg-slate-900/60 p-2.5 rounded-xl border border-slate-800">
        <div className="flex items-center space-x-1.5 flex-1">
          <label className="text-slate-400 font-mono text-[10px] uppercase">Parameter:</label>
          <select
            value={param}
            onChange={(e) => setParam(e.target.value)}
            className="bg-slate-900 text-white font-mono font-bold text-xs rounded-lg px-2.5 py-1.5 border border-slate-700 focus:outline-none flex-1"
          >
            {PARAM_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value} className="bg-slate-900 text-white font-mono font-bold">
                {opt.label}
              </option>
            ))}
          </select>
        </div>

        <div className="flex items-center space-x-2">
          <label className="text-slate-400 font-mono text-[10px] uppercase">Change (%):</label>
          <input
            type="number"
            step="1"
            value={pct}
            onChange={(e) => setPct(parseFloat(e.target.value) || 0)}
            className="w-16 bg-slate-900 text-white font-mono font-bold text-xs rounded-lg px-2 py-1.5 border border-slate-700 focus:outline-none text-center"
          />
        </div>

        <button
          onClick={handleSimulate}
          disabled={loading}
          className="flex items-center space-x-1.5 px-3.5 py-1.5 rounded-xl text-white font-bold text-xs transition-all disabled:opacity-50"
          style={{
            background: 'linear-gradient(135deg, #3b82f6, #2563eb)',
            boxShadow: '0 4px 12px -2px rgba(59, 130, 246, 0.4)',
          }}
        >
          <Play className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          <span>{loading ? 'Simulating...' : 'Run Scenario'}</span>
        </button>
      </div>

      {/* Results Box */}
      <div className="flex-1 overflow-y-auto pr-1 space-y-3 text-xs">
        {!result ? (
          <div className="h-full flex flex-col items-center justify-center text-slate-500 font-mono space-y-2">
            <Sliders className="w-8 h-8 opacity-40 animate-pulse" />
            <p>Select a telemetry parameter and modification percentage above to run physics simulation.</p>
          </div>
        ) : (
          <>
            {/* Simulation Label Banner */}
            <div className="p-2.5 rounded-xl bg-blue-500/10 border border-blue-500/30 flex items-center justify-between font-mono">
              <span className="font-bold text-blue-300">{result.simulation_label}</span>
              <span className="text-[10px] text-slate-400">
                Mean: {result.original_mean} → <strong className="text-amber-400">{result.simulated_mean}</strong>
              </span>
            </div>

            {/* Downstream Effects */}
            <div className="space-y-2">
              <h4 className="font-bold text-slate-300 uppercase tracking-wider text-[10px] font-mono">
                Downstream Physics Cascades
              </h4>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 font-mono">
                {downstream.map((eff: any, idx: number) => (
                  <div key={idx} className="p-2.5 rounded-xl bg-slate-900/80 border border-slate-800 space-y-1">
                    <div className="flex items-center justify-between text-[11px]">
                      <span className="font-bold text-slate-200">{eff.parameter}</span>
                      <span
                        className={`font-bold text-[10px] ${
                          eff.change_percent >= 0 ? 'text-amber-400' : 'text-cyan-400'
                        }`}
                      >
                        {eff.change_percent >= 0 ? `+${eff.change_percent}%` : `${eff.change_percent}%`}
                      </span>
                    </div>

                    <div className="text-[10px] text-slate-400 flex items-center space-x-1">
                      <span>{eff.original_mean} {eff.unit}</span>
                      <ArrowRight className="w-3 h-3 text-slate-500" />
                      <span className="font-bold text-sky-300">{eff.simulated_mean} {eff.unit}</span>
                    </div>

                    <div className="text-[9px] text-purple-400 truncate" title={eff.equation}>
                      eq: {eff.equation}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Health & Physics Check Row */}
            <div className="grid grid-cols-2 gap-2 font-mono text-[10px]">
              <div className="p-2.5 rounded-xl bg-slate-900/80 border border-slate-800 space-y-1">
                <span className="text-slate-400 block uppercase">Simulated System Health</span>
                <span
                  className={`text-xs font-bold uppercase ${
                    health.assessment === 'NOMINAL'
                      ? 'text-emerald-400'
                      : health.assessment === 'WARNING'
                      ? 'text-amber-400'
                      : 'text-rose-400'
                  }`}
                >
                  {health.assessment} ({health.total_violations} Threshold Violations)
                </span>
              </div>

              <div className="p-2.5 rounded-xl bg-slate-900/80 border border-slate-800 space-y-1">
                <span className="text-slate-400 block uppercase">Physics Consistency</span>
                <span
                  className={`text-xs font-bold uppercase ${
                    physics.overall_consistent ? 'text-emerald-400' : 'text-rose-400'
                  }`}
                >
                  {physics.overall_consistent ? 'PASSED (0 residual drift)' : 'VIOLATION DETECTED'}
                </span>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
};
