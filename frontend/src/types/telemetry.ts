export interface TelemetryDataPoint {
  id?: number;
  timestamp: number;
  flight_phase: string;
  is_imputed?: boolean;
  P_chamber?: number | null;
  T_chamber?: number | null;
  m_ox?: number | null;
  m_fuel?: number | null;
  F_thrust?: number | null;
  N_pump?: number | null;
  P_tank_lox?: number | null;
  P_tank_fuel?: number | null;
  vib_x?: number | null;
  vib_y?: number | null;
  vib_z?: number | null;
  acc_axial?: number | null;
  v_batt?: number | null;
  i_bus?: number | null;
  T_skin?: number | null;
  rate_roll?: number | null;
  rate_pitch?: number | null;
  rate_yaw?: number | null;
}

export interface AnomalyItem {
  id?: number;
  timestamp: number;
  parameter: string;
  anomaly_type: 'GAP' | 'DRIFT' | 'NOISE' | 'STUCK' | 'SPIKE' | 'PHYSICS_VIOLATION';
  severity: 'INFO' | 'WARNING' | 'CRITICAL';
  description: string;
  value_observed?: number | null;
  expected_range_min?: number | null;
  expected_range_max?: number | null;
  confidence: number;
  flight_phase?: string;
  created_at?: string;
}

export interface ImputationItem {
  id?: number;
  timestamp: number;
  parameter: string;
  original_value?: number | null;
  imputed_value: number;
  confidence_score: number;
  gap_duration: number;
  method_used: string;
  physics_residual?: number;
}

export interface AlertItem {
  id?: number;
  timestamp: number;
  level: 'INFO' | 'WARNING' | 'CRITICAL';
  title: string;
  message: string;
  parameter?: string;
  is_acknowledged?: boolean;
  created_at?: string;
}

export interface SubsystemHealthItem {
  score: number | null;
  status: string;
  has_data: boolean;
}

export interface SystemHealthInfo {
  score: number;
  status: 'NOMINAL' | 'ATTENTION_REQUIRED' | 'WARNING' | 'CRITICAL_HAZARD';
  total_records: number;
  anomalies_summary: {
    critical: number;
    warning: number;
    info: number;
  };
  subsystem_health?: Record<string, SubsystemHealthItem>;
}

