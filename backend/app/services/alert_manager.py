import numpy as np
import pandas as pd
from typing import List, Dict, Any
from app.services.synthetic_data import (
    PARAM_METADATA, ISP, G0, K_CHAMBER,
    THRUST_TOLERANCE_KN, PRESSURE_TOLERANCE_MPA, MASS_FLOW_TOLERANCE_KGS,
    TEMPERATURE_TOLERANCE_K, OF_RATIO_TOLERANCE
)

# =============================================================================
# HEALTH PENALTY CONSTANTS — Authoritative values (matches documentation)
# Applied per GROUPED EVENT, not per individual sample
# =============================================================================
HEALTH_PENALTY_CRITICAL = 8.0
HEALTH_PENALTY_WARNING = 3.5
HEALTH_PENALTY_INFO = 1.0


# Subsystem categorization for health incident grouping and subsystem health
SUBSYSTEM_MAP = {
    "vib_x": "VIBRATION",
    "vib_y": "VIBRATION",
    "vib_z": "VIBRATION",
    "rate_roll": "GUIDANCE",
    "rate_pitch": "GUIDANCE",
    "rate_yaw": "GUIDANCE",
    "acc_axial": "GUIDANCE",
    "v_batt": "ELECTRICAL",
    "i_bus": "ELECTRICAL",
    "P_tank_lox": "PROPULSION",
    "P_tank_fuel": "PROPULSION",
    "T_skin": "THERMAL",
    "P_chamber": "PROPULSION",
    "T_chamber": "PROPULSION",
    "m_ox": "PROPULSION",
    "m_fuel": "PROPULSION",
    "F_thrust": "PROPULSION",
    "N_pump": "PROPULSION",
    "MIXTURE_RATIO_O_F": "PROPULSION",
    "SYSTEM_LINK": "COMMUNICATIONS",
}

SUBSYSTEM_DEFINITIONS = {
    "PROPULSION": ["P_chamber", "T_chamber", "m_ox", "m_fuel", "F_thrust", "N_pump", "MIXTURE_RATIO_O_F", "P_tank_lox", "P_tank_fuel"],
    "THERMAL": ["T_skin"],
    "POWER / ELECT": ["v_batt", "i_bus"],
    "GUIDANCE / NAV": ["rate_roll", "rate_pitch", "rate_yaw", "acc_axial", "vib_x", "vib_y", "vib_z"],
}


class AlertManagerService:
    def group_anomalies_for_health_scoring(
        self, anomalies: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Groups raw or multi-detector anomaly findings into independent System Health Incidents.
        
        Rules:
        1. Vibration anomalies (vib_x, vib_y, vib_z) occurring within proximity (within 10.0s or overlapping)
           are grouped into 1 Vibration Incident.
        2. Multiple detector findings for the same parameter in proximity (within 5.0s)
           are merged into 1 Parameter Incident.
        3. Cascading engine/propulsion anomalies occurring at the same time window
           are merged into 1 Propulsion Incident.
        4. Brief 1-sample noise/spike chatter in non-faulty parameters (duration < 0.5s)
           is classified as INFO severity to reflect minor signal noise rather than vehicle structural failure.
        5. Genuinely distinct failures in different subsystems (e.g., v_batt STUCK vs P_tank_lox DRIFT)
           or different time windows remain SEPARATE health incidents.
        """
        if not anomalies:
            return []

        # Prepare normalized items
        items = []
        for a in anomalies:
            item = dict(a)
            t_start = float(item.get("timestamp", 0.0))
            dur = float(item.get("duration", 0.0))
            t_end_val = item.get("end_time")
            t_end = float(t_end_val) if t_end_val is not None else (t_start + dur)
            item["_t_start"] = t_start
            item["_t_end"] = max(t_end, t_start)
            param = item.get("parameter", "UNKNOWN")
            item["_subsystem"] = SUBSYSTEM_MAP.get(param, "OTHER")
            
            # Identify primary vs secondary transient findings
            atype = item.get("anomaly_type", "")
            detector = item.get("detector", "")
            val_obs = item.get("value_observed")
            
            is_primary_fault = (
                atype in ["GAP", "STUCK", "DRIFT", "PHYSICS_VIOLATION"] or
                detector == "range_violation" or
                (atype == "NOISE" and dur >= 5.0) or
                (atype == "SPIKE" and dur >= 0.5) or
                (param == "T_skin" and val_obs is not None and val_obs > 600.0)
            )
            
            if not is_primary_fault and dur < 0.5 and atype == "SPIKE":
                # Minor 1-sample transient spike -> INFO level for health model
                item["severity"] = "INFO"
                
            items.append(item)

        # Sort chronologically by start time
        items.sort(key=lambda x: (x["_t_start"], x["_t_end"]))

        incidents: List[Dict[str, Any]] = []
        for item in items:
            merged = False
            for inc in incidents:
                # Vibration subsystem uses 10.0s proximity buffer to merge related vibration disturbance chatter
                proximity_buffer = 10.0 if (item["_subsystem"] == "VIBRATION" and inc["_subsystem"] == "VIBRATION") else 5.0
                
                time_overlap = (
                    item["_t_start"] <= inc["_t_end"] + proximity_buffer and
                    inc["_t_start"] <= item["_t_end"] + proximity_buffer
                )
                
                if not time_overlap:
                    continue

                # Criteria for merging into the same health incident:
                same_param = (item.get("parameter") == inc.get("parameter"))
                both_vibration = (item["_subsystem"] == "VIBRATION" and inc["_subsystem"] == "VIBRATION")
                same_subsystem = (item["_subsystem"] == inc["_subsystem"])

                if same_param or both_vibration or same_subsystem:
                    # Merge into existing incident
                    inc["_t_start"] = min(inc["_t_start"], item["_t_start"])
                    inc["_t_end"] = max(inc["_t_end"], item["_t_end"])
                    inc["duration"] = round(inc["_t_end"] - inc["_t_start"], 2)
                    inc["timestamp"] = inc["_t_start"]
                    
                    # Highest severity wins
                    sev_map = {"CRITICAL": 3, "WARNING": 2, "INFO": 1}
                    if sev_map.get(item.get("severity", "INFO"), 1) > sev_map.get(inc.get("severity", "INFO"), 1):
                        inc["severity"] = item["severity"]
                        
                    # Highest confidence wins
                    inc["confidence"] = max(inc.get("confidence", 1.0), item.get("confidence", 1.0))
                    
                    # Track combined parameters
                    params = set(inc.get("_params_list", [inc.get("parameter")]))
                    params.add(item.get("parameter"))
                    inc["_params_list"] = list(params)
                    
                    merged = True
                    break

            if not merged:
                new_inc = dict(item)
                new_inc["_params_list"] = [item.get("parameter")]
                incidents.append(new_inc)

        # Transitive merge pass: fully consolidate overlapping same-subsystem health incidents
        changed = True
        while changed:
            changed = False
            new_incidents = []
            for inc in incidents:
                merged_with_existing = False
                for existing in new_incidents:
                    proximity_buffer = 10.0 if (inc["_subsystem"] == "VIBRATION" and existing["_subsystem"] == "VIBRATION") else 5.0
                    time_overlap = (
                        inc["_t_start"] <= existing["_t_end"] + proximity_buffer and
                        existing["_t_start"] <= inc["_t_end"] + proximity_buffer
                    )
                    same_subsystem = (inc["_subsystem"] == existing["_subsystem"])
                    same_param = (inc.get("parameter") == existing.get("parameter"))
                    both_vibration = (inc["_subsystem"] == "VIBRATION" and existing["_subsystem"] == "VIBRATION")
                    
                    if time_overlap and (same_param or both_vibration or same_subsystem):
                        existing["_t_start"] = min(existing["_t_start"], inc["_t_start"])
                        existing["_t_end"] = max(existing["_t_end"], inc["_t_end"])
                        existing["duration"] = round(existing["_t_end"] - existing["_t_start"], 2)
                        existing["timestamp"] = existing["_t_start"]
                        sev_map = {"CRITICAL": 3, "WARNING": 2, "INFO": 1}
                        if sev_map.get(inc.get("severity", "INFO"), 1) > sev_map.get(existing.get("severity", "INFO"), 1):
                            existing["severity"] = inc["severity"]
                        existing["confidence"] = max(existing.get("confidence", 1.0), inc.get("confidence", 1.0))
                        merged_with_existing = True
                        changed = True
                        break
                if not merged_with_existing:
                    new_incidents.append(inc)
            incidents = new_incidents

        return incidents

    def generate_alerts_from_anomalies(
        self, anomalies: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Generates priority alerts based on detected anomaly events."""
        alerts = []
        for idx, a in enumerate(anomalies):
            sev = a.get("severity", "WARNING")
            param = a.get("parameter", "UNKNOWN")
            atype = a.get("anomaly_type", "ANOMALY")
            t = a.get("timestamp", 0.0)
            desc = a.get("description", "")
            
            if sev == "CRITICAL":
                title = f"CRITICAL HAZARD: {param} {atype}"
                msg = f"Immediate telemetry surveillance required at T+{t:.1f}s. {desc}"
            elif sev == "WARNING":
                title = f"WARNING: {param} {atype} Detected"
                msg = f"Anomalous telemetry trajectory observed at T+{t:.1f}s. {desc}"
            else:
                title = f"INFO: {param} Nominal Deviation"
                msg = f"Informational system event log at T+{t:.1f}s."
                
            alerts.append({
                "id": idx + 1,
                "timestamp": t,
                "level": sev,
                "title": title,
                "message": msg,
                "parameter": param,
                "is_acknowledged": False
            })
            
        return alerts

    def _get_status_from_score(self, score: float) -> str:
        """Authoritative status mapping based on health score threshold configuration."""
        if score >= 90.0:
            return "NOMINAL"
        elif score >= 75.0:
            return "ATTENTION_REQUIRED"
        elif score >= 55.0:
            return "WARNING"
        else:
            return "CRITICAL_HAZARD"

    def calculate_system_health_score(
        self, df: pd.DataFrame, anomalies: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Calculates overall launch vehicle health score (0 to 100) and genuine subsystem breakdown.
        
        Operates on GROUPED SYSTEM HEALTH INCIDENTS to prevent health score collapse.
        Subsystem scores are calculated strictly from actual telemetry/anomaly data belonging
        to each subsystem.
        """
        empty_subsystem_health = {}
        for sub_name in SUBSYSTEM_DEFINITIONS.keys():
            empty_subsystem_health[sub_name] = {"score": None, "status": "INSUFFICIENT_DATA", "has_data": False}

        if df.empty:
            return {
                "score": 100.0,
                "status": "NOMINAL",
                "total_records": 0,
                "anomalies_summary": {"critical": 0, "warning": 0, "info": 0},
                "event_count": 0,
                "subsystem_health": empty_subsystem_health,
            }
        
        # Deduplicate/group raw findings into independent health incidents
        grouped_events = self.group_anomalies_for_health_scoring(anomalies)
        
        # Count events by severity
        n_critical = sum(1 for a in grouped_events if a.get("severity") == "CRITICAL")
        n_warning = sum(1 for a in grouped_events if a.get("severity") == "WARNING")
        n_info = sum(1 for a in grouped_events if a.get("severity") == "INFO")
        
        # Helper to compute deduction for a list of events
        def _calc_deduction(events_list: List[Dict[str, Any]]) -> float:
            total_ded = 0.0
            for event in events_list:
                sev = event.get("severity", "INFO")
                duration = event.get("duration", 0.0)
                confidence = event.get("confidence", 1.0)
                
                if sev == "CRITICAL":
                    base_penalty = HEALTH_PENALTY_CRITICAL
                elif sev == "WARNING":
                    base_penalty = HEALTH_PENALTY_WARNING
                else:
                    base_penalty = HEALTH_PENALTY_INFO
                
                duration_factor = min(1.5, 1.0 + 0.5 * np.log2(1.0 + max(0, duration) / 10.0))
                penalty = min(12.0, base_penalty * duration_factor * confidence)
                total_ded += penalty
            return total_ded

        total_deduction = _calc_deduction(grouped_events)
        score = max(0.0, min(100.0, 100.0 - total_deduction))
        status = self._get_status_from_score(score)
        
        # Calculate genuine subsystem breakdown
        subsystem_health = {}
        for sub_name, params in SUBSYSTEM_DEFINITIONS.items():
            # Check if dataset has parameters belonging to this subsystem
            has_params = any(p in df.columns for p in params)
            if not has_params:
                subsystem_health[sub_name] = {
                    "score": None,
                    "status": "INSUFFICIENT_DATA",
                    "has_data": False,
                }
            else:
                sub_events = [
                    e for e in grouped_events
                    if e.get("parameter") in params or any(p in params for p in e.get("_params_list", []))
                ]
                sub_deduction = _calc_deduction(sub_events)
                sub_score = max(0.0, min(100.0, 100.0 - sub_deduction))
                sub_status = self._get_status_from_score(sub_score)
                subsystem_health[sub_name] = {
                    "score": round(sub_score, 1),
                    "status": sub_status,
                    "has_data": True,
                }

        return {
            "score": round(score, 1),
            "status": status,
            "total_records": len(df),
            "anomalies_summary": {
                "critical": n_critical,
                "warning": n_warning,
                "info": n_info
            },
            "event_count": len(grouped_events),
            "subsystem_health": subsystem_health,
        }


    def calculate_physics_compliance(
        self, df: pd.DataFrame
    ) -> Dict[str, Any]:
        """Calculates physics compliance from actual physics residuals.
        
        NOT from anomaly count / telemetry count.
        
        For each applicable physical relationship, computes:
            normalized_error = min(abs(residual) / tolerance, 1.0)
            compliance = 100 * (1 - weighted_normalized_error)
        
        Reports per-relationship and overall compliance.
        """
        result = {
            "overall": 100.0,
            "thrust": {"compliance": 100.0, "mean_residual_kN": 0.0, "max_residual_kN": 0.0, "samples": 0},
            "pressure": {"compliance": 100.0, "mean_residual_MPa": 0.0, "max_residual_MPa": 0.0, "samples": 0},
            "mass_flow": {"compliance": 100.0, "mean_residual_ratio": 0.0, "samples": 0},
        }
        
        if df.empty:
            return result
        
        compliances = []
        weights = []
        
        # --- 1. Thrust Physics Compliance ---
        # F_expected = (m_ox + m_fuel) * Isp * g0 / 1000 [kN]
        if all(col in df.columns for col in ["F_thrust", "m_ox", "m_fuel"]):
            valid = df.dropna(subset=["F_thrust", "m_ox", "m_fuel"])
            # Only evaluate during active firing (non-trivial flow)
            firing = valid[(valid["m_ox"] > 10.0) | (valid["m_fuel"] > 5.0)]
            if len(firing) > 0:
                expected_thrust = (firing["m_ox"] + firing["m_fuel"]) * ISP * G0 / 1000.0
                thrust_residuals = np.abs(firing["F_thrust"] - expected_thrust)
                mean_res = float(thrust_residuals.mean())
                max_res = float(thrust_residuals.max())
                
                # Normalized error per sample, then average
                norm_errors = np.minimum(thrust_residuals / THRUST_TOLERANCE_KN, 1.0)
                thrust_compliance = float(100.0 * (1.0 - norm_errors.mean()))
                
                result["thrust"] = {
                    "compliance": round(thrust_compliance, 1),
                    "mean_residual_kN": round(mean_res, 4),
                    "max_residual_kN": round(max_res, 4),
                    "tolerance_kN": THRUST_TOLERANCE_KN,
                    "samples": len(firing)
                }
                compliances.append(thrust_compliance)
                weights.append(3.0)  # Thrust is most important
        
        # --- 2. Chamber Pressure Physics Compliance ---
        # P_expected = k * (m_ox + m_fuel) [MPa]
        if all(col in df.columns for col in ["P_chamber", "m_ox", "m_fuel"]):
            valid = df.dropna(subset=["P_chamber", "m_ox", "m_fuel"])
            firing = valid[(valid["m_ox"] > 10.0) | (valid["m_fuel"] > 5.0)]
            if len(firing) > 0:
                expected_pressure = K_CHAMBER * (firing["m_ox"] + firing["m_fuel"])
                pressure_residuals = np.abs(firing["P_chamber"] - expected_pressure)
                mean_res = float(pressure_residuals.mean())
                max_res = float(pressure_residuals.max())
                
                norm_errors = np.minimum(pressure_residuals / PRESSURE_TOLERANCE_MPA, 1.0)
                pressure_compliance = float(100.0 * (1.0 - norm_errors.mean()))
                
                result["pressure"] = {
                    "compliance": round(pressure_compliance, 1),
                    "mean_residual_MPa": round(mean_res, 4),
                    "max_residual_MPa": round(max_res, 4),
                    "tolerance_MPa": PRESSURE_TOLERANCE_MPA,
                    "samples": len(firing)
                }
                compliances.append(pressure_compliance)
                weights.append(2.0)
        
        # --- 3. Mass-Flow Consistency (O/F Ratio) ---
        if all(col in df.columns for col in ["m_ox", "m_fuel"]):
            valid = df.dropna(subset=["m_ox", "m_fuel"])
            firing = valid[(valid["m_ox"] > 50.0) & (valid["m_fuel"] > 20.0)]
            if len(firing) > 0:
                of_ratio = firing["m_ox"] / firing["m_fuel"]
                ratio_deviation = np.abs(of_ratio - 2.5)
                mean_dev = float(ratio_deviation.mean())
                
                norm_errors = np.minimum(ratio_deviation / OF_RATIO_TOLERANCE, 1.0)
                ratio_compliance = float(100.0 * (1.0 - norm_errors.mean()))
                
                result["mass_flow"] = {
                    "compliance": round(ratio_compliance, 1),
                    "mean_residual_ratio": round(mean_dev, 4),
                    "nominal_ratio": 2.5,
                    "tolerance": OF_RATIO_TOLERANCE,
                    "samples": len(firing)
                }
                compliances.append(ratio_compliance)
                weights.append(1.0)
        
        # --- Overall weighted compliance ---
        if compliances:
            weights = np.array(weights)
            compliances = np.array(compliances)
            result["overall"] = round(float(np.average(compliances, weights=weights)), 1)
        
        return result

    def generate_comprehensive_flight_report(
        self, df: pd.DataFrame, anomalies: List[Dict[str, Any]], alerts: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generates detailed JSON launch mission surveillance report."""
        health = self.calculate_system_health_score(df, anomalies)
        physics = self.calculate_physics_compliance(df)
        
        subsystem_report = {}
        for sub_k, sub_v in health["subsystem_health"].items():
            subsystem_report[sub_k] = sub_v["status"]
            
        return {
            "title": "ISRO AERIS Launch Vehicle Health & Telemetry Analysis Report",
            "mission_id": "AERIS-LV-2026",
            "generated_at_t_plus": float(df["timestamp"].max()) if not df.empty and "timestamp" in df.columns else 600.0,
            "overall_health_score": health["score"],
            "system_status": health["status"],
            "physics_compliance": physics,
            "physics_compliance_score": f"{physics['overall']:.1f}%",
            "summary": {
                "total_telemetry_records": len(df),
                "total_anomalies": len(anomalies),
                "total_anomaly_events": len(anomalies),
                "total_alerts": len(alerts),
                "critical_count": health["anomalies_summary"]["critical"],
                "warning_count": health["anomalies_summary"]["warning"],
                "info_count": health["anomalies_summary"]["info"]
            },
            "subsystem_health": subsystem_report,
            "anomalies_catalog": anomalies[:30],
            "priority_alerts": alerts[:30]
        }


alert_manager = AlertManagerService()
