"""
Analysis Router — New API endpoints for:
  - Phase-relative anomaly detection (Phase 4)
  - Parametric scatter analysis (Phase 5)
  - Anomaly deep-dive (Phase 6)
  - Predictive drift monitor (Phase 9)
  - Mission what-if simulator (Phase 10)
  - Evaluation summary (Phase 15)
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import pandas as pd
import numpy as np

from app.database import get_db
from app.models.telemetry import TelemetryRecord, ImputationRecord
from app.models.anomaly import AnomalyRecord
from app.services.phase_anomaly_detector import phase_detector
from app.services.drift_monitor import drift_monitor
from app.services.whatif_simulator import whatif_simulator
from app.services.deep_dive import deep_dive_service
from app.services.alert_manager import alert_manager
from app.services.synthetic_data import PARAM_METADATA, ISP, G0, K_CHAMBER

router = APIRouter(prefix="/analysis", tags=["Advanced Analysis"])


def _build_telemetry_df(db: Session) -> pd.DataFrame:
    """Helper: builds full telemetry DataFrame from DB."""
    records = db.query(TelemetryRecord).order_by(TelemetryRecord.timestamp.asc()).all()
    if not records:
        return pd.DataFrame()
    data = []
    cols = ["timestamp", "flight_phase"] + list(PARAM_METADATA.keys())
    for r in records:
        d = {"timestamp": r.timestamp, "flight_phase": r.flight_phase}
        for col in PARAM_METADATA.keys():
            d[col] = getattr(r, col, None)
        data.append(d)
    return pd.DataFrame(data)


def clean_float(val):
    if val is None:
        return None
    try:
        f = float(val)
        if np.isnan(f) or np.isinf(f):
            return None
        return f
    except Exception:
        return None


# =========================================================================
# Phase 4: Phase-Relative Anomaly Detection
# =========================================================================
@router.get("/phase-baselines")
def get_phase_baselines(db: Session = Depends(get_db)):
    """Returns per-phase/per-parameter baseline statistics computed from telemetry data."""
    df = _build_telemetry_df(db)
    if df.empty:
        raise HTTPException(status_code=404, detail="No telemetry data available.")
    baselines = phase_detector.compute_phase_baselines(df)
    return {"baselines": baselines, "total_phases": len(baselines)}


@router.get("/phase-anomalies")
def get_phase_anomalies(db: Session = Depends(get_db)):
    """Detects phase-relative anomalies using z-scores from reference data."""
    df = _build_telemetry_df(db)
    if df.empty:
        raise HTTPException(status_code=404, detail="No telemetry data available.")
    anomalies = phase_detector.detect_phase_anomalies(df)
    return {
        "total_phase_anomalies": len(anomalies),
        "anomalies": anomalies[:100],  # Limit response size
    }


# =========================================================================
# Phase 5: Parametric Scatter Analysis
# =========================================================================
@router.get("/scatter")
def get_scatter_data(
    x_param: str = Query(..., description="X-axis parameter name"),
    y_param: str = Query(..., description="Y-axis parameter name"),
    phase: Optional[str] = Query(None, description="Optional flight phase filter"),
    anomaly_filter: Optional[str] = Query(None, description="Optional anomaly filter: ALL, NORMAL, ANOMALOUS"),
    db: Session = Depends(get_db),
):
    """Returns scatter plot data for two parameters with physical correlation & anomaly metadata."""
    if x_param not in PARAM_METADATA:
        raise HTTPException(status_code=400, detail=f"Unknown parameter: {x_param}")
    if y_param not in PARAM_METADATA:
        raise HTTPException(status_code=400, detail=f"Unknown parameter: {y_param}")

    df = _build_telemetry_df(db)
    if df.empty:
        raise HTTPException(status_code=404, detail="No telemetry data available.")

    # Filter by phase if specified
    if phase and phase.upper() != "ALL":
        df = df[df["flight_phase"] == phase.upper()]

    if df.empty:
        return {
            "x_param": x_param,
            "y_param": y_param,
            "x_unit": PARAM_METADATA[x_param].get("unit", ""),
            "y_unit": PARAM_METADATA[y_param].get("unit", ""),
            "total_points": 0,
            "points": [],
            "correlation_r": None,
            "correlation_label": "No Data",
        }

    # Fetch anomaly records for detailed mapping
    anomaly_recs = db.query(AnomalyRecord).all()
    anomaly_map = {}
    for a in anomaly_recs:
        t_rounded = round(float(a.timestamp), 1)
        anomaly_map[(a.parameter, t_rounded)] = a

    points = []
    for _, row in df.iterrows():
        x_val = row.get(x_param)
        y_val = row.get(y_param)
        if x_val is None or y_val is None:
            continue
        if isinstance(x_val, float) and np.isnan(x_val):
            continue
        if isinstance(y_val, float) and np.isnan(y_val):
            continue

        ts = round(float(row["timestamp"]), 1)
        anom_x = anomaly_map.get((x_param, ts))
        anom_y = anomaly_map.get((y_param, ts))
        matched_anom = anom_x or anom_y

        is_anomalous = bool(matched_anom is not None)

        if anomaly_filter == "NORMAL" and is_anomalous:
            continue
        if anomaly_filter == "ANOMALOUS" and not is_anomalous:
            continue

        pt = {
            "x": round(float(x_val), 4),
            "y": round(float(y_val), 4),
            "timestamp": ts,
            "flight_phase": str(row.get("flight_phase", "")),
            "is_anomalous": is_anomalous,
        }
        if matched_anom:
            pt["anomaly_id"] = matched_anom.id
            pt["anomaly_type"] = matched_anom.anomaly_type
            pt["severity"] = matched_anom.severity

        points.append(pt)

    # Downsample if too many points while preserving ALL anomalies & phase proportions
    if len(points) > 2500:
        anomalous_points = [p for p in points if p["is_anomalous"]]
        normal_points = [p for p in points if not p["is_anomalous"]]
        
        # Sample normal points evenly per flight phase
        sampled_normal = []
        phase_groups = {}
        for p in normal_points:
            ph = p["flight_phase"]
            phase_groups.setdefault(ph, []).append(p)
        
        target_per_phase = max(100, 2000 // max(1, len(phase_groups)))
        for ph, p_list in phase_groups.items():
            if len(p_list) <= target_per_phase:
                sampled_normal.extend(p_list)
            else:
                step = max(1, len(p_list) // target_per_phase)
                sampled_normal.extend(p_list[::step])

        points = sampled_normal + anomalous_points

    # Sort by timestamp
    points.sort(key=lambda p: p["timestamp"])

    # Calculate Pearson correlation coefficient
    x_arr = np.array([p["x"] for p in points], dtype=float)
    y_arr = np.array([p["y"] for p in points], dtype=float)

    correlation_r = None
    correlation_label = "Insufficient Variation"

    if len(x_arr) > 5:
        std_x = np.std(x_arr)
        std_y = np.std(y_arr)
        if std_x > 1e-6 and std_y > 1e-6:
            r_mat = np.corrcoef(x_arr, y_arr)
            r_val = float(r_mat[0, 1])
            if not np.isnan(r_val):
                correlation_r = round(r_val, 4)
                abs_r = abs(r_val)
                if abs_r >= 0.8:
                    correlation_label = "Strong Correlation"
                elif abs_r >= 0.5:
                    correlation_label = "Moderate Correlation"
                elif abs_r >= 0.25:
                    correlation_label = "Weak Correlation"
                else:
                    correlation_label = "No Linear Correlation"

    anomalous_count = sum(1 for p in points if p["is_anomalous"])

    return {
        "x_param": x_param,
        "y_param": y_param,
        "x_unit": PARAM_METADATA[x_param].get("unit", ""),
        "y_unit": PARAM_METADATA[y_param].get("unit", ""),
        "total_points": len(points),
        "nominal_count": len(points) - anomalous_count,
        "anomalous_count": anomalous_count,
        "correlation_r": correlation_r,
        "correlation_label": correlation_label,
        "points": points,
    }


# =========================================================================
# Phase 6: Anomaly Deep-Dive
# =========================================================================
@router.get("/anomaly/{anomaly_id}/deep-dive")
def get_anomaly_deep_dive(anomaly_id: int, db: Session = Depends(get_db)):
    """Returns comprehensive investigation data for a specific anomaly."""
    anomaly_rec = db.query(AnomalyRecord).filter(AnomalyRecord.id == anomaly_id).first()
    if not anomaly_rec:
        raise HTTPException(status_code=404, detail=f"Anomaly {anomaly_id} not found.")

    anomaly_dict = {
        "id": anomaly_rec.id,
        "timestamp": anomaly_rec.timestamp,
        "parameter": anomaly_rec.parameter,
        "anomaly_type": anomaly_rec.anomaly_type,
        "severity": anomaly_rec.severity,
        "description": anomaly_rec.description,
        "value_observed": anomaly_rec.value_observed,
        "expected_range_min": anomaly_rec.expected_range_min,
        "expected_range_max": anomaly_rec.expected_range_max,
        "confidence": anomaly_rec.confidence or 1.0,
        "flight_phase": anomaly_rec.flight_phase or "UNKNOWN",
    }

    df = _build_telemetry_df(db)
    if df.empty:
        raise HTTPException(status_code=404, detail="No telemetry data available.")

    deep_dive = deep_dive_service.generate_deep_dive(anomaly_dict, df)
    return deep_dive


# =========================================================================
# Phase 9: Predictive Drift Monitor
# =========================================================================
@router.get("/drift")
def get_drift_analysis(
    parameter: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Returns predictive drift analysis for all or a specific parameter."""
    df = _build_telemetry_df(db)
    if df.empty:
        raise HTTPException(status_code=404, detail="No telemetry data available.")

    if parameter:
        if parameter not in PARAM_METADATA:
            raise HTTPException(status_code=400, detail=f"Unknown parameter: {parameter}")
        result = drift_monitor.get_drift_for_parameter(df, parameter)
        if result is None:
            return {"parameter": parameter, "status": "insufficient_data"}
        return result

    results = drift_monitor.analyze_drift(df)
    return {
        "total_parameters_analyzed": len(results),
        "meaningful_trends": len([r for r in results if r.get("is_meaningful")]),
        "approaching_threshold": len([r for r in results if r.get("trend_status") == "approaching_threshold"]),
        "results": results,
    }


# =========================================================================
# Phase 10: Mission What-If Simulator
# =========================================================================
@router.post("/whatif")
def run_whatif_simulation(
    parameter: str = Query(..., description="Parameter to modify"),
    modification_pct: float = Query(0.0, description="Percentage modification (e.g. -5.0 for -5%)"),
    modification_abs: Optional[float] = Query(None, description="Absolute modification (overrides pct)"),
    db: Session = Depends(get_db),
):
    """Runs a what-if simulation by modifying a telemetry parameter."""
    if parameter not in PARAM_METADATA:
        raise HTTPException(status_code=400, detail=f"Unknown parameter: {parameter}")

    df = _build_telemetry_df(db)
    if df.empty:
        raise HTTPException(status_code=404, detail="No telemetry data available.")

    result = whatif_simulator.simulate(df, parameter, modification_pct, modification_abs)
    return result


# =========================================================================
# Phase 15: Evaluation Summary
# =========================================================================
@router.get("/evaluation-summary")
def get_evaluation_summary(db: Session = Depends(get_db)):
    """Returns a comprehensive evaluation summary of the entire mission."""
    df = _build_telemetry_df(db)
    anomaly_recs = db.query(AnomalyRecord).all()
    imputation_recs = db.query(ImputationRecord).all()

    # Mission stats
    mission = {
        "total_records": len(df),
        "sensors": len(PARAM_METADATA),
        "sensor_names": list(PARAM_METADATA.keys()),
        "flight_phases": list(df["flight_phase"].unique()) if not df.empty else [],
        "duration_seconds": round(float(df["timestamp"].max() - df["timestamp"].min()), 2) if not df.empty else 0,
    }

    # Anomaly summary
    anom_types = {}
    anom_severities = {"CRITICAL": 0, "WARNING": 0, "INFO": 0}
    for a in anomaly_recs:
        anom_types[a.anomaly_type] = anom_types.get(a.anomaly_type, 0) + 1
        if a.severity in anom_severities:
            anom_severities[a.severity] += 1

    anomaly_summary = {
        "total": len(anomaly_recs),
        "by_type": anom_types,
        "by_severity": anom_severities,
    }

    # Recovery summary
    methods_used = {}
    for imp in imputation_recs:
        methods_used[imp.method_used] = methods_used.get(imp.method_used, 0) + 1

    recovery_summary = {
        "total_imputed_points": len(imputation_recs),
        "methods_used": methods_used,
        "avg_confidence": round(float(np.mean([i.confidence_score for i in imputation_recs])), 4) if imputation_recs else None,
        "avg_physics_residual": round(float(np.mean([i.physics_residual for i in imputation_recs if i.physics_residual is not None])), 4) if any(i.physics_residual is not None for i in imputation_recs) else None,
    }

    # PINN model stats
    from app.ml.pinn_model import pinn_predictor
    pinn_summary = {
        "status": pinn_predictor.status,
        "is_trained": pinn_predictor.is_trained,
        "metadata": pinn_predictor.metadata if pinn_predictor.metadata else {},
    }

    # Physics compliance
    physics_compliance = {}
    if not df.empty:
        full_df = df.copy()
        for col in ["P_chamber", "T_chamber", "m_ox", "m_fuel", "F_thrust", "N_pump"]:
            if col not in full_df.columns:
                full_df[col] = None
        physics_compliance = alert_manager.calculate_physics_compliance(full_df)

    # Health score
    anom_dicts = [
        {
            "severity": a.severity,
            "anomaly_type": a.anomaly_type,
            "parameter": a.parameter,
            "timestamp": a.timestamp,
            "duration": a.duration or 0.0,
            "end_time": a.end_time,
            "confidence": a.confidence or 1.0,
        }
        for a in anomaly_recs
    ]
    health_info = alert_manager.calculate_system_health_score(df, anom_dicts) if not df.empty else {}

    return {
        "mission": mission,
        "anomaly_summary": anomaly_summary,
        "recovery_summary": recovery_summary,
        "pinn_model": pinn_summary,
        "physics_compliance": physics_compliance,
        "health": health_info,
    }
