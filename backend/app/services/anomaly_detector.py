import numpy as np
import pandas as pd
from typing import List, Dict, Any, Optional, Tuple
from app.services.synthetic_data import (
    PARAM_METADATA, PHASE_EXPECTED_RANGES, PHASE_BOUNDARIES,
    ISP, G0, K_CHAMBER, is_phase_transition, OF_RATIO_MIN, OF_RATIO_MAX
)
from app.ml.feature_engine import extract_time_series_features
from app.ml.anomaly_classifier import ml_detector

# =============================================================================
# DETECTION CAPABILITY MAP — Which parameters support which anomaly types
# =============================================================================
STUCK_ELIGIBLE_PARAMS = [
    "P_chamber", "T_chamber", "m_ox", "m_fuel", "F_thrust", "N_pump",
    "P_tank_lox", "P_tank_fuel", "v_batt", "i_bus", "T_skin"
]

DRIFT_ELIGIBLE_PARAMS = [
    "P_chamber", "T_chamber", "m_ox", "m_fuel", "F_thrust", "N_pump",
    "P_tank_lox", "P_tank_fuel", "v_batt", "i_bus"
]

# Parameter-specific noise thresholds (coefficient of variation multiplier)
# Higher values = more tolerant of noise for that parameter
NOISE_THRESHOLDS = {
    "P_chamber": 0.10,
    "T_chamber": 0.08,
    "m_ox": 0.10,
    "m_fuel": 0.10,
    "F_thrust": 0.10,
    "N_pump": 0.10,
    "P_tank_lox": 0.15,
    "P_tank_fuel": 0.15,
    "acc_axial": 0.20,
    "T_skin": 0.15,
    "i_bus": 0.15,
}
# rate_roll, rate_pitch, rate_yaw, v_batt are excluded from standard simple noise checks
# (vibrations vib_x, vib_y, vib_z are handled by dedicated phase-aware vibration noise detector)
NOISE_EXCLUDED_PARAMS = {"rate_roll", "rate_pitch", "rate_yaw", "v_batt"}


class AnomalyDetectorService:
    def detect_all_anomalies(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Runs multi-strategy anomaly detection across all 16 telemetry parameters.
        
        Returns a list of anomaly EVENTS (grouped contiguous samples), not
        individual per-sample records.
        """
        raw_anomalies = []
        if df.empty:
            return raw_anomalies
        
        timestamps = df["timestamp"].values
        dt = float(np.median(np.diff(timestamps))) if len(timestamps) > 1 else 0.1
        
        # 1. Check for GAP Anomalies (NaN values and RF link gaps)
        raw_anomalies.extend(self._detect_gap_anomalies(df, dt))
        
        # 2. Check Single-Parameter Statistical & Threshold Anomalies
        for param, meta in PARAM_METADATA.items():
            if param in df.columns:
                series = df[param]
                raw_anomalies.extend(self._detect_single_param_anomalies(df, param, series, meta))
                
        # 3. Check Phase-Aware Contextual Threshold Violations
        raw_anomalies.extend(self._detect_phase_contextual_anomalies(df))

        # 4. Check Multi-Parameter Physics Correlation Breakdown Anomalies
        raw_anomalies.extend(self._detect_correlation_breakdowns(df))

        # 5. Check Unsupervised Machine Learning (Isolation Forest) Anomalies
        ml_anom = ml_detector.detect_multivariate_ml_anomalies(df, list(PARAM_METADATA.keys()))
        # Filter duplicates if timestamp and parameter already reported
        existing_keys = {(a["timestamp"], a["parameter"]) for a in raw_anomalies}
        for ma in ml_anom:
            if (ma["timestamp"], ma["parameter"]) not in existing_keys:
                raw_anomalies.append(ma)
                existing_keys.add((ma["timestamp"], ma["parameter"]))
        
        # 6. Group contiguous anomalies into events
        grouped = self._group_anomalies_into_events(raw_anomalies, df)
        
        # Sort events by start timestamp
        grouped.sort(key=lambda x: x["timestamp"])
        return grouped

    # =========================================================================
    # GAP Detection
    # =========================================================================
    def _detect_gap_anomalies(self, df: pd.DataFrame, expected_dt: float) -> List[Dict[str, Any]]:
        gaps = []
        timestamps = df["timestamp"].values
        
        # RF Link jump gaps
        diffs = np.diff(timestamps)
        jump_indices = np.where(diffs > expected_dt * 2.5)[0]
        for idx in jump_indices:
            start_t = float(timestamps[idx])
            end_t = float(timestamps[idx + 1])
            dur = end_t - start_t
            gaps.append({
                "timestamp": start_t,
                "end_time": end_t,
                "duration": dur,
                "parameter": "SYSTEM_LINK",
                "anomaly_type": "GAP",
                "severity": "CRITICAL" if dur > 5.0 else ("WARNING" if dur > 1.0 else "INFO"),
                "description": f"RF link data drop: {dur:.2f}s missing frame duration.",
                "value_observed": None,
                "expected_range_min": None,
                "expected_range_max": None,
                "confidence": 1.0,
                "flight_phase": str(df.loc[idx, "flight_phase"]) if "flight_phase" in df.columns else "UNKNOWN",
                "detector": "gap_nan"
            })

        # Parameter NaN gaps — grouped into events
        for param in PARAM_METADATA.keys():
            if param in df.columns:
                is_nan = df[param].isna().values
                if np.any(is_nan):
                    nan_indices = np.where(is_nan)[0]
                    groups = np.split(nan_indices, np.where(np.diff(nan_indices) != 1)[0] + 1)
                    meta = PARAM_METADATA.get(param, {"min": 0, "max": 100})
                    for group in groups:
                        if len(group) > 0:
                            start_t = float(timestamps[group[0]])
                            end_t = float(timestamps[group[-1]])
                            dur = end_t - start_t + expected_dt
                            is_core = param in ["P_chamber", "F_thrust", "m_ox", "m_fuel", "P_tank_lox"]
                            sev = "CRITICAL" if (dur > 5.0 or (dur > 1.0 and is_core)) else ("WARNING" if dur > 1.0 else "INFO")
                            gaps.append({
                                "timestamp": start_t,
                                "end_time": end_t + expected_dt,
                                "duration": round(dur, 2),
                                "parameter": param,
                                "anomaly_type": "GAP",
                                "severity": sev,
                                "description": f"Telemetry missing gap for {param}: {dur:.2f}s duration ({len(group)} samples).",
                                "value_observed": None,
                                "expected_range_min": meta["min"],
                                "expected_range_max": meta["max"],
                                "confidence": 1.0,
                                "sample_count": len(group),
                                "flight_phase": str(df.loc[group[0], "flight_phase"]) if "flight_phase" in df.columns else "UNKNOWN",
                                "detector": "gap_nan"
                            })
        return gaps

    # =========================================================================
    # Single-Parameter Anomalies: SPIKE, DRIFT, STUCK, NOISE
    # =========================================================================
    def _detect_single_param_anomalies(
        self, df: pd.DataFrame, param: str, series: pd.Series, meta: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        anomalies = []
        valid_series = series.dropna()
        if len(valid_series) < 10:
            return anomalies
        
        p_min, p_max = meta["min"], meta["max"]
        span = p_max - p_min
        rolling_mean, rolling_std, rate_of_change, z_score = extract_time_series_features(valid_series, window_size=15)
        
        timestamps = df["timestamp"].values

        # ----- 1. SPIKE Detection (phase-aware) -----
        anomalies.extend(self._detect_spikes(df, param, valid_series, meta, z_score, rolling_mean, rolling_std, timestamps))

        # ----- 2. DRIFT Detection (phase-aware, expanded param list) -----
        if param in DRIFT_ELIGIBLE_PARAMS:
            anomalies.extend(self._detect_drift(df, param, valid_series, meta, timestamps))

        # ----- 3. STUCK Detection (expanded param list) -----
        if param in STUCK_ELIGIBLE_PARAMS:
            anomalies.extend(self._detect_stuck(df, param, valid_series, meta, timestamps))

        # ----- 4. NOISE Detection (parameter-specific thresholds) -----
        if param not in NOISE_EXCLUDED_PARAMS:
            anomalies.extend(self._detect_noise(df, param, valid_series, meta, rolling_std, timestamps))
            
        return anomalies

    def _detect_spikes(
        self, df: pd.DataFrame, param: str, valid_series: pd.Series, 
        meta: Dict[str, Any], z_score: pd.Series,
        rolling_mean: pd.Series, rolling_std: pd.Series,
        timestamps: np.ndarray
    ) -> List[Dict[str, Any]]:
        """Phase-aware spike detection: combines range violations, z-score spikes,
        and robust median-based transient excursions while suppressing phase transition boundaries."""
        anomalies = []
        p_min, p_max = meta["min"], meta["max"]
        span = p_max - p_min
        flagged_indices = set()
        
        # 1. Out-of-bounds range violations
        out_of_bounds_indices = valid_series.index[(valid_series < p_min) | (valid_series > p_max)]
        if len(out_of_bounds_indices) > 0:
            groups = np.split(out_of_bounds_indices, np.where(np.diff(out_of_bounds_indices) != 1)[0] + 1)
            for group in groups:
                if len(group) > 0:
                    first_idx = group[0]
                    t = float(df.loc[first_idx, "timestamp"])
                    
                    if is_phase_transition(t, margin=3.0):
                        continue
                    
                    val = float(valid_series.loc[first_idx])
                    phase = str(df.loc[first_idx, "flight_phase"]) if "flight_phase" in df.columns else "UNKNOWN"
                    
                    phase_ranges = PHASE_EXPECTED_RANGES.get(phase, {})
                    if param in phase_ranges:
                        phase_min, phase_max = phase_ranges[param]
                        if phase_min <= val <= phase_max:
                            continue
                    
                    flagged_indices.update(group)
                    anomalies.append({
                        "timestamp": t,
                        "end_time": float(df.loc[group[-1], "timestamp"]),
                        "duration": float(df.loc[group[-1], "timestamp"]) - t,
                        "parameter": param,
                        "anomaly_type": "SPIKE",
                        "severity": "CRITICAL",
                        "description": f"Out-of-bounds reading for {param}: {val:.2f} {meta['unit']} (limit: [{p_min}, {p_max}])",
                        "value_observed": val,
                        "expected_range_min": p_min,
                        "expected_range_max": p_max,
                        "confidence": 0.99,
                        "sample_count": len(group),
                        "flight_phase": phase,
                        "detector": "range_violation"
                    })

        # 2. Robust median-based & statistical transient spikes (not already flagged)
        rolling_med = valid_series.rolling(window=15, min_periods=3, center=True).median().fillna(valid_series)
        median_dev = (valid_series - rolling_med).abs()
        
        # Robust spike condition: z-score > 4.5 OR median deviation > 15% span OR (z-score > 3.0 & median_dev > 50)
        is_spike = (
            (z_score.abs() > 4.5) | 
            (median_dev > span * 0.15) | 
            ((z_score.abs() > 3.0) & (median_dev > 50.0))
        ) & (~valid_series.index.isin(flagged_indices))
        
        # Vibration parameters in sustained noise regions (rolling_std > 3.5g) are NOISE, not SPIKE
        if param in {"vib_x", "vib_y", "vib_z"}:
            is_spike = is_spike & (rolling_std <= 3.5)
        
        spike_indices = valid_series.index[is_spike]
        if len(spike_indices) > 0:
            z_groups = np.split(spike_indices, np.where(np.diff(spike_indices) != 1)[0] + 1)
            for group in z_groups:
                if len(group) > 0:
                    idx = group[0]
                    t = float(df.loc[idx, "timestamp"])
                    
                    if is_phase_transition(t, margin=3.0):
                        continue
                    
                    val = float(valid_series.loc[idx])
                    z = float(z_score.loc[idx]) if idx in z_score.index else 0.0
                    mdev = float(median_dev.loc[idx])
                    phase = str(df.loc[idx, "flight_phase"]) if "flight_phase" in df.columns else "UNKNOWN"
                    rmean = float(rolling_mean.loc[idx]) if idx in rolling_mean.index else val
                    rstd = float(rolling_std.loc[idx]) if idx in rolling_std.index else 0.0
                    anomalies.append({
                        "timestamp": t,
                        "end_time": float(df.loc[group[-1], "timestamp"]),
                        "duration": float(df.loc[group[-1], "timestamp"]) - t,
                        "parameter": param,
                        "anomaly_type": "SPIKE",
                        "severity": "CRITICAL" if abs(z) > 6.0 or mdev > span * 0.25 else "WARNING",
                        "description": f"Transient spike in {param}: val={val:.2f}, median_dev={mdev:.2f}, z-score={z:.2f}",
                        "value_observed": val,
                        "expected_range_min": round(rmean - 3 * max(rstd, 1.0), 2),
                        "expected_range_max": round(rmean + 3 * max(rstd, 1.0), 2),
                        "confidence": 0.95,
                        "sample_count": len(group),
                        "flight_phase": phase,
                        "detector": "transient_spike"
                    })
        return anomalies

    def _detect_drift(
        self, df: pd.DataFrame, param: str, valid_series: pd.Series,
        meta: Dict[str, Any], timestamps: np.ndarray
    ) -> List[Dict[str, Any]]:
        """Phase-aware drift detection: Detects sustained monotonic deviation from
        phase-specific baseline. Does NOT classify stage transitions as drift."""
        anomalies = []
        p_min, p_max = meta["min"], meta["max"]
        span = p_max - p_min
        
        # Only analyze during active flight (after ignition)
        active_mask = df.loc[valid_series.index, "timestamp"] > 15.0
        steady_series = valid_series[active_mask]
        if len(steady_series) < 50:
            return anomalies
        
        # Get flight phases for each point
        phases = df.loc[steady_series.index, "flight_phase"]
        
        # Analyze drift within each flight phase separately
        for phase_name in phases.unique():
            phase_mask = phases == phase_name
            phase_series = steady_series[phase_mask]
            
            if len(phase_series) < 30:
                continue
            
            # Calculate rolling deviation from phase median (robust baseline)
            phase_median = phase_series.median()
            deviation = phase_series - phase_median
            
            # Use a sliding window to detect sustained unidirectional drift
            window = min(50, len(phase_series) // 3)
            if window < 10:
                continue
            
            rolling_dev = deviation.rolling(window=window, min_periods=window).mean()
            
            # Drift threshold: sustained deviation > 15% of parameter span
            drift_threshold = span * 0.15
            
            drift_hits = rolling_dev.abs() > drift_threshold
            if drift_hits.any():
                # Find the first sustained drift region
                first_drift_idx = drift_hits.idxmax()
                t = float(df.loc[first_drift_idx, "timestamp"])
                
                # Skip if near a phase transition
                if is_phase_transition(t, margin=5.0):
                    continue
                
                val = float(phase_series.loc[first_drift_idx])
                dev_val = float(rolling_dev.loc[first_drift_idx])
                
                # Find extent of drift
                drift_indices = phase_series.index[drift_hits.reindex(phase_series.index, fill_value=False)]
                end_t = float(df.loc[drift_indices[-1], "timestamp"]) if len(drift_indices) > 0 else t
                
                anomalies.append({
                    "timestamp": t,
                    "end_time": end_t,
                    "duration": round(end_t - t, 2),
                    "parameter": param,
                    "anomaly_type": "DRIFT",
                    "severity": "WARNING" if abs(dev_val) < span * 0.25 else "CRITICAL",
                    "description": f"Sensor drift detected in {param}: sustained {dev_val:+.3f} {meta['unit']} deviation from phase baseline during {phase_name}.",
                    "value_observed": val,
                    "expected_range_min": p_min,
                    "expected_range_max": p_max,
                    "confidence": min(0.95, 0.80 + abs(dev_val) / span),
                    "flight_phase": phase_name,
                    "detector": "phase_aware_drift"
                })
        
        return anomalies

    def _detect_stuck(
        self, df: pd.DataFrame, param: str, valid_series: pd.Series,
        meta: Dict[str, Any], timestamps: np.ndarray
    ) -> List[Dict[str, Any]]:
        """Stuck-at-fault detection: Flags parameters with zero variance over a
        sustained window during active flight. Includes v_batt, i_bus, T_skin."""
        anomalies = []
        p_min, p_max = meta["min"], meta["max"]
        
        # Only check during active flight
        active_series = valid_series[df.loc[valid_series.index, "timestamp"] > 15.0]
        if len(active_series) < 30:
            return anomalies
        
        stuck_window = 20
        rolling_var = active_series.rolling(window=stuck_window, min_periods=stuck_window).var().fillna(1.0)
        
        # Stuck = near-zero variance AND value is not near the parameter minimum
        # (i.e., not simply a parameter that's legitimately at zero during engine-off)
        stuck_mask = (rolling_var < 1e-7)
        
        # For engine parameters, also require the value to be meaningfully above zero
        engine_params = {"P_chamber", "T_chamber", "m_ox", "m_fuel", "F_thrust", "N_pump"}
        if param in engine_params:
            stuck_mask = stuck_mask & (active_series > meta.get("min", 0.0) + 0.05 * (p_max - p_min))
        
        # For v_batt/i_bus/T_skin, any sustained flatline is suspicious
        stuck_hits = np.where(stuck_mask)[0]
        if len(stuck_hits) > 0:
            # Group contiguous stuck regions
            groups = np.split(stuck_hits, np.where(np.diff(stuck_hits) != 1)[0] + 1)
            for group in groups:
                if len(group) < 5:  # Need at least 5 consecutive stuck points
                    continue
                
                first_idx = active_series.index[group[0]]
                last_idx = active_series.index[group[-1]]
                val = float(valid_series.loc[first_idx])
                t_start = float(df.loc[first_idx, "timestamp"])
                t_end = float(df.loc[last_idx, "timestamp"])
                
                # Skip if during engine-off phase for engine params
                phase = str(df.loc[first_idx, "flight_phase"]) if "flight_phase" in df.columns else "UNKNOWN"
                if param in engine_params and phase in ["PRE_LAUNCH", "STAGE_SEPARATION", "COAST_ORBIT"]:
                    continue
                
                anomalies.append({
                    "timestamp": t_start,
                    "end_time": t_end,
                    "duration": round(t_end - t_start, 2),
                    "parameter": param,
                    "anomaly_type": "STUCK",
                    "severity": "CRITICAL",
                    "description": f"Stuck-at-fault detected in {param}: flatline value={val:.2f} {meta['unit']} for {t_end-t_start:.1f}s.",
                    "value_observed": val,
                    "expected_range_min": p_min,
                    "expected_range_max": p_max,
                    "confidence": 0.98,
                    "sample_count": len(group),
                    "flight_phase": phase,
                    "detector": "stuck_variance"
                })
        
        return anomalies

    def _detect_noise(
        self, df: pd.DataFrame, param: str, valid_series: pd.Series,
        meta: Dict[str, Any], rolling_std: pd.Series, timestamps: np.ndarray
    ) -> List[Dict[str, Any]]:
        """Parameter-specific noise detection.
        Supports standard parameters and phase-aware vibration noise detection for vib_x, vib_y, vib_z."""
        anomalies = []
        p_min, p_max = meta["min"], meta["max"]
        span = p_max - p_min
        
        # Vibration parameters require phase-aware thresholds
        if param in {"vib_x", "vib_y", "vib_z"}:
            phases = df.loc[valid_series.index, "flight_phase"] if "flight_phase" in df.columns else pd.Series("UNKNOWN", index=valid_series.index)
            is_noisy = []
            for idx in valid_series.index:
                t = float(df.loc[idx, "timestamp"])
                rstd = float(rolling_std.loc[idx]) if idx in rolling_std.index else 0.0
                phase = str(phases.loc[idx])
                
                # Dynamic threshold: MAX_Q & STAGE_SEPARATION have high normal aero/pyro vibration
                thresh = 10.0 if phase in ["MAX_Q", "STAGE_SEPARATION"] else 3.5
                if rstd > thresh and not is_phase_transition(t, margin=3.0):
                    is_noisy.append(idx)
                    
            if len(is_noisy) > 0:
                groups = np.split(is_noisy, np.where(np.diff(is_noisy) != 1)[0] + 1)
                for group in groups:
                    if len(group) >= 5:
                        first_idx = group[0]
                        last_idx = group[-1]
                        t_start = float(df.loc[first_idx, "timestamp"])
                        t_end = float(df.loc[last_idx, "timestamp"])
                        phase = str(df.loc[first_idx, "flight_phase"]) if "flight_phase" in df.columns else "UNKNOWN"
                        rstd = float(rolling_std.loc[first_idx])
                        anomalies.append({
                            "timestamp": t_start,
                            "end_time": t_end,
                            "duration": round(t_end - t_start, 2),
                            "parameter": param,
                            "anomaly_type": "NOISE",
                            "severity": "WARNING" if rstd < 10.0 else "CRITICAL",
                            "description": f"Excessive vibration noise in {param}: σ={rstd:.2f}g (threshold exceeded during {phase}).",
                            "value_observed": float(valid_series.loc[first_idx]),
                            "expected_range_min": p_min,
                            "expected_range_max": p_max,
                            "confidence": 0.92,
                            "sample_count": len(group),
                            "flight_phase": phase,
                            "detector": "phase_vibration_noise"
                        })
            return anomalies

        # Standard non-vibration parameters
        noise_threshold = NOISE_THRESHOLDS.get(param, 0.15)
        high_noise = np.where(rolling_std > span * noise_threshold)[0]
        
        if len(high_noise) > 0:
            groups = np.split(high_noise, np.where(np.diff(high_noise) != 1)[0] + 1)
            for group in groups:
                if len(group) < 10:
                    continue
                
                first_idx = valid_series.index[group[0]]
                last_idx = valid_series.index[group[-1]]
                t_start = float(df.loc[first_idx, "timestamp"])
                t_end = float(df.loc[last_idx, "timestamp"])
                
                if is_phase_transition(t_start, margin=5.0):
                    continue
                
                noise_level = float(rolling_std.iloc[group[0]])
                phase = str(df.loc[first_idx, "flight_phase"]) if "flight_phase" in df.columns else "UNKNOWN"
                
                anomalies.append({
                    "timestamp": t_start,
                    "end_time": t_end,
                    "duration": round(t_end - t_start, 2),
                    "parameter": param,
                    "anomaly_type": "NOISE",
                    "severity": "WARNING" if noise_level < span * 0.25 else "CRITICAL",
                    "description": f"High frequency noise contamination in {param}: σ={noise_level:.3f} {meta['unit']} (threshold: {span*noise_threshold:.3f}).",
                    "value_observed": float(valid_series.loc[first_idx]),
                    "expected_range_min": p_min,
                    "expected_range_max": p_max,
                    "confidence": 0.90,
                    "sample_count": len(group),
                    "flight_phase": phase,
                    "detector": "rolling_std_noise"
                })
        
        return anomalies

    # =========================================================================
    # Phase-Contextual Anomalies
    # =========================================================================
    def _detect_phase_contextual_anomalies(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Evaluates parameter behaviors against specific flight phase expectations."""
        anomalies = []
        if "flight_phase" not in df.columns:
            return anomalies

        # 1. COAST_ORBIT phase: Engine thrust and flow should be near zero
        coast_mask = (df["flight_phase"] == "COAST_ORBIT")
        if coast_mask.any():
            coast_df = df[coast_mask]
            if "F_thrust" in coast_df.columns:
                high_thrust = coast_df[coast_df["F_thrust"] > 10.0]
                if not high_thrust.empty:
                    first_row = high_thrust.iloc[0]
                    anomalies.append({
                        "timestamp": float(first_row["timestamp"]),
                        "parameter": "F_thrust",
                        "anomaly_type": "PHYSICS_VIOLATION",
                        "severity": "CRITICAL",
                        "description": f"Unexpected engine thrust ({first_row['F_thrust']:.1f} kN) during COAST_ORBIT phase!",
                        "value_observed": float(first_row["F_thrust"]),
                        "expected_range_min": 0.0,
                        "expected_range_max": 2.0,
                        "confidence": 0.99,
                        "flight_phase": "COAST_ORBIT",
                        "detector": "phase_contextual"
                    })

        # 2. PRE_LAUNCH phase: Flow rates should be near zero
        pre_mask = (df["flight_phase"] == "PRE_LAUNCH")
        if pre_mask.any():
            pre_df = df[pre_mask]
            if "m_ox" in pre_df.columns:
                flow = pre_df[pre_df["m_ox"] > 5.0]
                if not flow.empty:
                    first_row = flow.iloc[0]
                    anomalies.append({
                        "timestamp": float(first_row["timestamp"]),
                        "parameter": "m_ox",
                        "anomaly_type": "PHYSICS_VIOLATION",
                        "severity": "CRITICAL",
                        "description": f"Propellant flow ({first_row['m_ox']:.1f} kg/s) detected prior to engine ignition!",
                        "value_observed": float(first_row["m_ox"]),
                        "expected_range_min": 0.0,
                        "expected_range_max": 2.0,
                        "confidence": 0.98,
                        "flight_phase": "PRE_LAUNCH",
                        "detector": "phase_contextual"
                    })

        return anomalies

    # =========================================================================
    # Multi-Parameter Physics Correlation Anomalies
    # =========================================================================
    def _detect_correlation_breakdowns(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Detects violations of cross-parameter physical laws."""
        anomalies = []

        # 1. Thrust vs Flow Rate correlation
        if "m_ox" in df.columns and "F_thrust" in df.columns:
            m_ox_clean = df["m_ox"].fillna(0.0)
            m_fuel_clean = df["m_fuel"].fillna(0.0) if "m_fuel" in df.columns else pd.Series(0.0, index=df.index)
            thrust_clean = df["F_thrust"].fillna(0.0)
            
            # Flowing fuel (>50 kg/s) but near-zero thrust during main stage flight
            mask = (
                (df["timestamp"] > 15.0) & (df["timestamp"] < 140.0) & 
                (m_ox_clean > 50.0) & (thrust_clean < 20.0)
            )
            viol_indices = np.where(mask)[0]
            if len(viol_indices) > 0:
                idx = viol_indices[0]
                anomalies.append({
                    "timestamp": float(df.loc[idx, "timestamp"]),
                    "parameter": "F_thrust",
                    "anomaly_type": "PHYSICS_VIOLATION",
                    "severity": "CRITICAL",
                    "description": "Mass flow active without corresponding engine thrust generation (Combustion failure!).",
                    "value_observed": float(thrust_clean[idx]),
                    "expected_range_min": 800.0,
                    "expected_range_max": 1050.0,
                    "confidence": 0.99,
                    "flight_phase": str(df.loc[idx, "flight_phase"]) if "flight_phase" in df.columns else "STAGE_1_FLIGHT",
                    "detector": "physics_correlation"
                })

        # 2. Chamber Pressure vs Turbopump Speed
        if "P_chamber" in df.columns and "N_pump" in df.columns:
            pc = df["P_chamber"].fillna(0.0)
            npump = df["N_pump"].fillna(0.0)
            mask_pump = (df["timestamp"] > 15.0) & (npump > 20000.0) & (pc < 1.0)
            viol_indices = np.where(mask_pump)[0]
            if len(viol_indices) > 0:
                idx = viol_indices[0]
                anomalies.append({
                    "timestamp": float(df.loc[idx, "timestamp"]),
                    "parameter": "P_chamber",
                    "anomaly_type": "PHYSICS_VIOLATION",
                    "severity": "CRITICAL",
                    "description": "High turbopump RPM with zero chamber pressure (Feed system rupture hazard!).",
                    "value_observed": float(pc[idx]),
                    "expected_range_min": 4.0,
                    "expected_range_max": 8.0,
                    "confidence": 0.98,
                    "flight_phase": str(df.loc[idx, "flight_phase"]) if "flight_phase" in df.columns else "STAGE_1_FLIGHT",
                    "detector": "physics_correlation"
                })

        # 3. Oxidizer to Fuel Mixture Ratio (O/F)
        if "m_ox" in df.columns and "m_fuel" in df.columns:
            m_ox = df["m_ox"].fillna(0.0)
            m_fuel = df["m_fuel"].fillna(0.0)
            firing_mask = (m_ox > 50.0) & (m_fuel > 20.0)
            if firing_mask.any():
                of_ratio = m_ox[firing_mask] / m_fuel[firing_mask]
                # Nominal O/F ratio ~ 2.5, acceptable OF_RATIO_MIN - OF_RATIO_MAX
                anom_of = of_ratio[(of_ratio < OF_RATIO_MIN) | (of_ratio > OF_RATIO_MAX)]
                if not anom_of.empty:
                    idx = anom_of.index[0]
                    ratio_val = float(anom_of.iloc[0])
                    anomalies.append({
                        "timestamp": float(df.loc[idx, "timestamp"]),
                        "parameter": "MIXTURE_RATIO_O_F",
                        "anomaly_type": "PHYSICS_VIOLATION",
                        "severity": "WARNING",
                        "description": f"Propellant mixture ratio O/F out of nominal envelope ({ratio_val:.2f}, expected {OF_RATIO_MIN}-{OF_RATIO_MAX})",
                        "value_observed": ratio_val,
                        "expected_range_min": OF_RATIO_MIN,
                        "expected_range_max": OF_RATIO_MAX,
                        "confidence": 0.92,
                        "flight_phase": str(df.loc[idx, "flight_phase"]) if "flight_phase" in df.columns else "STAGE_1_FLIGHT",
                        "detector": "physics_correlation"
                    })

        return anomalies

    # =========================================================================
    # Anomaly Event Grouping
    # =========================================================================
    def _group_anomalies_into_events(
        self, raw_anomalies: List[Dict[str, Any]], df: pd.DataFrame
    ) -> List[Dict[str, Any]]:
        """Groups contiguous/overlapping anomaly records of the same parameter or subsystem
        into single events to prevent duplicate event penalties.
        """
        if not raw_anomalies:
            return []
            
        items = [dict(a) for a in raw_anomalies]
        for a in items:
            t_start = float(a.get("timestamp", 0.0))
            dur = float(a.get("duration", 0.0))
            t_end = float(a.get("end_time", t_start + dur))
            a["_t_start"] = t_start
            a["_t_end"] = max(t_end, t_start)
            
        # Sort chronologically by start time
        items.sort(key=lambda x: (x["_t_start"], x["_t_end"]))
        
        merged_events: List[Dict[str, Any]] = []
        for item in items:
            merged = False
            for prev in merged_events:
                same_param = (item.get("parameter") == prev.get("parameter"))
                both_vib = (item.get("parameter") in ["vib_x", "vib_y", "vib_z"] and prev.get("parameter") in ["vib_x", "vib_y", "vib_z"])
                
                buffer = 10.0 if both_vib else 3.0
                time_overlap = (
                    item["_t_start"] <= prev["_t_end"] + buffer and
                    prev["_t_start"] <= item["_t_end"] + buffer
                )
                
                if time_overlap and (same_param or both_vib):
                    prev["_t_start"] = min(prev["_t_start"], item["_t_start"])
                    prev["_t_end"] = max(prev["_t_end"], item["_t_end"])
                    prev["timestamp"] = prev["_t_start"]
                    prev["end_time"] = prev["_t_end"]
                    prev["duration"] = round(prev["_t_end"] - prev["_t_start"], 2)
                    prev["sample_count"] = prev.get("sample_count", 1) + item.get("sample_count", 1)
                    
                    # Primary fault type precedence: GAP > STUCK > DRIFT > PHYSICS_VIOLATION > NOISE > SPIKE
                    type_priority = {"GAP": 6, "STUCK": 5, "DRIFT": 4, "PHYSICS_VIOLATION": 3, "NOISE": 2, "SPIKE": 1}
                    if type_priority.get(item.get("anomaly_type", ""), 0) > type_priority.get(prev.get("anomaly_type", ""), 0):
                        prev["anomaly_type"] = item["anomaly_type"]
                    
                    sev_order = {"CRITICAL": 3, "WARNING": 2, "INFO": 1}
                    if sev_order.get(item.get("severity", "INFO"), 0) > sev_order.get(prev.get("severity", "INFO"), 0):
                        prev["severity"] = item["severity"]
                    if item.get("confidence", 0) > prev.get("confidence", 0):
                        prev["confidence"] = item["confidence"]
                        
                    merged = True
                    break
                    
            if not merged:
                merged_events.append(dict(item))
                
        return merged_events


anomaly_service = AnomalyDetectorService()
