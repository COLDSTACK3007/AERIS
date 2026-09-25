import React, { useState, useEffect } from 'react';
import { Header } from './components/Common/Header';
import { Sidebar } from './components/Common/Sidebar';
import { HealthScore } from './components/Dashboard/HealthScore';
import { TelemetryPanel } from './components/Dashboard/TelemetryPanel';
import { AnomalyTimeline } from './components/Dashboard/AnomalyTimeline';
import { ImputationView } from './components/Dashboard/ImputationView';
import { CorrelationHeatmap } from './components/Dashboard/CorrelationHeatmap';
import { FlightPhaseOverlay } from './components/Dashboard/FlightPhaseOverlay';
import { AlertPanel } from './components/Dashboard/AlertPanel';
import { ReportView } from './components/Dashboard/ReportView';
import { AnomalyDeepDive } from './components/Dashboard/AnomalyDeepDive';
import { ScatterAnalysis } from './components/Dashboard/ScatterAnalysis';
import { DriftMonitor } from './components/Dashboard/DriftMonitor';
import { WhatIfSimulator } from './components/Dashboard/WhatIfSimulator';
import { EvaluationSummary } from './components/Dashboard/EvaluationSummary';
import { api } from './services/api';
import { TelemetryDataPoint, AnomalyItem, ImputationItem, AlertItem, SystemHealthInfo } from './types/telemetry';

export function App() {
  const [theme, setTheme] = useState<'dark' | 'light'>('light');
  const [activeTab, setActiveTab] = useState<string>('dashboard');
  const [telemetry, setTelemetry] = useState<TelemetryDataPoint[]>([]);
  const [anomalies, setAnomalies] = useState<AnomalyItem[]>([]);
  const [imputations, setImputations] = useState<ImputationItem[]>([]);
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [healthInfo, setHealthInfo] = useState<SystemHealthInfo | null>(null);
  const [correlationMatrix, setCorrelationMatrix] = useState<Record<string, Record<string, number>>>({});
  
  const [isGenerating, setIsGenerating] = useState(false);
  const [isDetecting, setIsDetecting] = useState(false);
  const [isImputing, setIsImputing] = useState(false);
  const [selectedAnomalyId, setSelectedAnomalyId] = useState<number | null>(null);

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme((prev) => (prev === 'dark' ? 'light' : 'dark'));
  };

  const fetchAllData = async () => {
    try {
      const data = await api.getTelemetryData();
      setTelemetry(data);

      const health = await api.getHealth();
      setHealthInfo(health);

      const anoms = await api.getAnomalies();
      setAnomalies(anoms);

      const imps = await api.getImputations();
      setImputations(imps);

      const alrts = await api.getAlerts();
      setAlerts(alrts);

      const summary = await api.getSummary();
      if (summary.correlation_matrix) {
        setCorrelationMatrix(summary.correlation_matrix);
      }
    } catch (err) {
      console.error('Failed to fetch dashboard data:', err);
    }
  };

  useEffect(() => {
    fetchAllData();

    // WebSocket real-time stream listener connection
    let ws: WebSocket | null = null;
    try {
      const defaultWsUrl = typeof window !== 'undefined' && window.location.hostname !== 'localhost'
        ? `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/api/telemetry/stream`
        : 'ws://localhost:8000/api/telemetry/stream';
      const wsUrl = import.meta.env.VITE_WS_BASE_URL || defaultWsUrl;
      ws = new WebSocket(wsUrl);
      ws.onmessage = (event) => {
        try {
          const newPoint = JSON.parse(event.data);
          if (newPoint && newPoint.timestamp !== undefined) {
            setTelemetry((prev) => [...prev.slice(-500), newPoint]);
          }
        } catch (e) {
          // ignore non-json frames
        }
      };
    } catch (e) {
      console.warn('WebSocket connection failed:', e);
    }

    return () => {
      if (ws) ws.close();
    };
  }, []);

  const handleGenerateSynthetic = async () => {
    setIsGenerating(true);
    try {
      await api.generateSynthetic(600.0, true);
      await fetchAllData();
    } catch (err) {
      console.error(err);
    } finally {
      setIsGenerating(false);
    }
  };

  const handleUploadCSV = async (file: File) => {
    try {
      const res = await api.uploadCSV(file);
      await fetchAllData();
      alert(`CSV Uploaded Successfully!\nFile: ${file.name}\nRows Ingested: ${res.rows_ingested}`);
    } catch (err: any) {
      console.error('Failed to upload CSV:', err);
      const detail = err.response?.data?.detail || err.message || 'Unknown error';
      alert(`Failed to process CSV telemetry file:\n${detail}`);
    }
  };

  const handleRunAnomalyDetection = async () => {
    setIsDetecting(true);
    try {
      const res = await api.runAnomalyDetection();
      await fetchAllData();
      alert(`Anomaly Detection Completed!\nDetected: ${res.total_anomalies_detected} anomalies`);
    } catch (err: any) {
      console.error('Anomaly detection failed:', err);
      const detail = err.response?.data?.detail || err.message || 'Error running detector';
      alert(`Anomaly Detection Failed:\n${detail}`);
    } finally {
      setIsDetecting(false);
    }
  };

  const handleRunImputation = async () => {
    setIsImputing(true);
    try {
      const res = await api.runImputation();
      await fetchAllData();
      alert(`Physics Imputation Completed!\nImputed: ${res.total_imputed_points} data points`);
    } catch (err: any) {
      console.error('Physics imputation failed:', err);
      const detail = err.response?.data?.detail || err.message || 'Error running imputation';
      alert(`Physics Imputation Failed:\n${detail}`);
    } finally {
      setIsImputing(false);
    }
  };

  const handleNavClick = (tabId: string) => {
    setActiveTab(tabId);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const activePhase = telemetry.length > 0 
    ? (telemetry[telemetry.length - 1].flight_phase || 'STAGE_1_FLIGHT') 
    : 'PRE_LAUNCH';

  const currentTs = telemetry.length > 0 ? telemetry[telemetry.length - 1].timestamp : 0;

  return (
    <div className="min-h-screen p-3 sm:p-6 transition-colors duration-300" style={{ background: 'var(--bg-primary)' }}>
      <Header
        onRefresh={fetchAllData}
        onGenerateSynthetic={handleGenerateSynthetic}
        onUploadCSV={handleUploadCSV}
        isGenerating={isGenerating}
        activeFlightPhase={activePhase}
        theme={theme}
        toggleTheme={toggleTheme}
      />

      <div className="flex flex-col lg:flex-row gap-4 sm:gap-6 items-start">
        <Sidebar activeTab={activeTab} setActiveTab={handleNavClick} />

        <main className="flex-1 space-y-6 min-w-0">
          <FlightPhaseOverlay currentTimestamp={currentTs} />

          {/* Page 1: Live Dashboard */}
          {activeTab === 'dashboard' && (
            <div className="space-y-6 animate-fadeIn">
              <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
                <div className="lg:col-span-3">
                  <TelemetryPanel data={telemetry} />
                </div>
                <div className="lg:col-span-1">
                  <HealthScore healthInfo={healthInfo} />
                </div>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <AnomalyTimeline
                  anomalies={anomalies}
                  onRunDetection={handleRunAnomalyDetection}
                  isDetecting={isDetecting}
                  onSelectAnomaly={(id) => setSelectedAnomalyId(id)}
                />
                <AlertPanel alerts={alerts} />
              </div>
            </div>
          )}

          {/* Page 2: Telemetry Stream */}
          {activeTab === 'telemetry' && (
            <div className="space-y-6 animate-fadeIn">
              <div className="flex items-center space-x-2 border-b border-[var(--divider)] pb-2.5">
                <span className="w-2.5 h-2.5 rounded-full bg-[var(--accent-cyan)] shadow-sm" />
                <h2 className="text-xs font-bold font-mono tracking-widest uppercase text-[var(--text-main)]">
                  Telemetry Stream Analysis
                </h2>
              </div>
              <TelemetryPanel data={telemetry} />
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <ScatterAnalysis onSelectAnomaly={(id) => setSelectedAnomalyId(id)} />
                <CorrelationHeatmap matrix={correlationMatrix} />
              </div>
            </div>
          )}

          {/* Page 3: Anomaly Engine */}
          {activeTab === 'anomalies' && (
            <div className="space-y-6 animate-fadeIn">
              <div className="flex items-center space-x-2 border-b border-[var(--divider)] pb-2.5">
                <span className="w-2.5 h-2.5 rounded-full bg-[var(--accent-rose)] shadow-sm" />
                <h2 className="text-xs font-bold font-mono tracking-widest uppercase text-[var(--text-main)]">
                  Anomaly Engine, Parametric Scatter & Predictive Drift
                </h2>
              </div>
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <div className="lg:col-span-2">
                  <AnomalyTimeline
                    anomalies={anomalies}
                    onRunDetection={handleRunAnomalyDetection}
                    isDetecting={isDetecting}
                    onSelectAnomaly={(id) => setSelectedAnomalyId(id)}
                  />
                </div>
                <div className="lg:col-span-1">
                  <AlertPanel alerts={alerts} />
                </div>
              </div>
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <div className="lg:col-span-1">
                  <ScatterAnalysis onSelectAnomaly={(id) => setSelectedAnomalyId(id)} />
                </div>
                <div className="lg:col-span-2">
                  <DriftMonitor />
                </div>
              </div>
            </div>
          )}

          {/* Page 4: Physics Imputation */}
          {activeTab === 'imputation' && (
            <div className="space-y-6 animate-fadeIn">
              <div className="flex items-center space-x-2 border-b border-[var(--divider)] pb-2.5">
                <span className="w-2.5 h-2.5 rounded-full bg-[var(--isro-orange)] shadow-sm" />
                <h2 className="text-xs font-bold font-mono tracking-widest uppercase text-[var(--text-main)]">
                  Physics-Constrained Imputation Engine & Scenario Simulator
                </h2>
              </div>
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <ImputationView
                  imputations={imputations}
                  onRunImputation={handleRunImputation}
                  isImputing={isImputing}
                />
                <WhatIfSimulator />
              </div>
              <div className="grid grid-cols-1 gap-6">
                <CorrelationHeatmap matrix={correlationMatrix} />
              </div>
            </div>
          )}

          {/* Page 5: Predictive Drift */}
          {activeTab === 'prediction' && (
            <div className="space-y-6 animate-fadeIn">
              <div className="flex items-center space-x-2 border-b border-[var(--divider)] pb-2.5">
                <span className="w-2.5 h-2.5 rounded-full bg-purple-400 shadow-sm" />
                <h2 className="text-xs font-bold font-mono tracking-widest uppercase text-[var(--text-main)]">
                  Predictive Drift Monitor & Threshold Crossing Analysis
                </h2>
              </div>
              <DriftMonitor />
            </div>
          )}

          {/* Page 5: Mission Evaluation Summary */}
          {activeTab === 'evaluation' && (
            <div className="space-y-6 animate-fadeIn">
              <div className="flex items-center space-x-2 border-b border-[var(--divider)] pb-2.5">
                <span className="w-2.5 h-2.5 rounded-full bg-amber-400 shadow-sm" />
                <h2 className="text-xs font-bold font-mono tracking-widest uppercase text-[var(--text-main)]">
                  Mission Evaluation & Model Metrics
                </h2>
              </div>
              <EvaluationSummary />
            </div>
          )}

          {/* Page 6: Flight Reports */}
          {activeTab === 'reports' && (
            <div className="space-y-6 animate-fadeIn">
              <div className="flex items-center space-x-2 border-b border-[var(--divider)] pb-2.5">
                <span className="w-2.5 h-2.5 rounded-full bg-[var(--accent-blue)] shadow-sm" />
                <h2 className="text-xs font-bold font-mono tracking-widest uppercase text-[var(--text-main)]">
                  Mission Flight Reports & Data Exports
                </h2>
              </div>
              <ReportView />
            </div>
          )}
        </main>
      </div>

      {/* Anomaly Deep-Dive Modal Overlay */}
      <AnomalyDeepDive
        anomalyId={selectedAnomalyId}
        onClose={() => setSelectedAnomalyId(null)}
      />
    </div>
  );
}

export default App;
