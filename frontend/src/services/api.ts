import axios from 'axios';
import { TelemetryDataPoint, AnomalyItem, ImputationItem, AlertItem, SystemHealthInfo } from '../types/telemetry';

const API_BASE = import.meta.env.VITE_API_BASE_URL || (typeof window !== 'undefined' && window.location.hostname === 'localhost' ? 'http://localhost:8000/api' : '/api');

export const api = {
  // Telemetry
  getTelemetryData: async (startTime?: number, endTime?: number, parameters?: string[]): Promise<TelemetryDataPoint[]> => {
    const params: any = {};
    if (startTime !== undefined) params.start_time = startTime;
    if (endTime !== undefined) params.end_time = endTime;
    if (parameters) params.parameters = parameters.join(',');
    const res = await axios.get(`${API_BASE}/telemetry/data`, { params });
    return res.data;
  },

  getParameterMetadata: async () => {
    const res = await axios.get(`${API_BASE}/telemetry/parameters`);
    return res.data;
  },

  uploadCSV: async (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    const res = await axios.post(`${API_BASE}/telemetry/upload`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return res.data;
  },

  // Synthetic Data
  generateSynthetic: async (duration: number = 600, injectAnomalies: boolean = true) => {
    const res = await axios.post(`${API_BASE}/synthetic/generate`, null, {
      params: { duration, inject_anomalies: injectAnomalies },
    });
    return res.data;
  },

  // Anomaly Detection
  runAnomalyDetection: async () => {
    const res = await axios.post(`${API_BASE}/anomaly/detect`);
    return res.data;
  },

  getAnomalies: async (): Promise<AnomalyItem[]> => {
    const res = await axios.get(`${API_BASE}/anomaly/results`);
    return res.data;
  },

  // Imputation
  runImputation: async () => {
    const res = await axios.post(`${API_BASE}/imputation/run`);
    return res.data;
  },

  getImputations: async (): Promise<ImputationItem[]> => {
    const res = await axios.get(`${API_BASE}/imputation/results`);
    return res.data;
  },

  // Alerts & Dashboard
  getAlerts: async (): Promise<AlertItem[]> => {
    const res = await axios.get(`${API_BASE}/alerts`);
    return res.data;
  },

  acknowledgeAlert: async (alertId: number) => {
    const res = await axios.post(`${API_BASE}/alerts/acknowledge/${alertId}`);
    return res.data;
  },

  getHealth: async (): Promise<SystemHealthInfo> => {
    const res = await axios.get(`${API_BASE}/dashboard/health`);
    return res.data;
  },

  getSummary: async () => {
    const res = await axios.get(`${API_BASE}/dashboard/summary`);
    return res.data;
  },

  generateReport: async () => {
    const res = await axios.post(`${API_BASE}/alerts/reports/generate`);
    return res.data;
  },

  // Analysis & Deep-Dive (Phase 4, 5, 6, 9, 10, 15)
  getPhaseBaselines: async () => {
    const res = await axios.get(`${API_BASE}/analysis/phase-baselines`);
    return res.data;
  },

  getPhaseAnomalies: async () => {
    const res = await axios.get(`${API_BASE}/analysis/phase-anomalies`);
    return res.data;
  },

  getScatterData: async (xParam: string, yParam: string, phase?: string, anomalyFilter?: string) => {
    const params: any = { x_param: xParam, y_param: yParam };
    if (phase && phase !== 'ALL') params.phase = phase;
    if (anomalyFilter && anomalyFilter !== 'ALL') params.anomaly_filter = anomalyFilter;
    const res = await axios.get(`${API_BASE}/analysis/scatter`, { params });
    return res.data;
  },

  getAnomalyDeepDive: async (anomalyId: number) => {
    const res = await axios.get(`${API_BASE}/analysis/anomaly/${anomalyId}/deep-dive`);
    return res.data;
  },

  getDriftAnalysis: async (parameter?: string) => {
    const params: any = {};
    if (parameter) params.parameter = parameter;
    const res = await axios.get(`${API_BASE}/analysis/drift`, { params });
    return res.data;
  },

  runWhatIf: async (parameter: string, modificationPct: number = 0, modificationAbs?: number) => {
    const params: any = { parameter, modification_pct: modificationPct };
    if (modificationAbs !== undefined) params.modification_abs = modificationAbs;
    const res = await axios.post(`${API_BASE}/analysis/whatif`, null, { params });
    return res.data;
  },

  getEvaluationSummary: async () => {
    const res = await axios.get(`${API_BASE}/analysis/evaluation-summary`);
    return res.data;
  }
};
