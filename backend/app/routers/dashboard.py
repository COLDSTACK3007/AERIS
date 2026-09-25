from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
import pandas as pd
import numpy as np

from app.database import get_db
from app.models.telemetry import TelemetryRecord, ImputationRecord
from app.models.anomaly import AnomalyRecord
from app.services.alert_manager import alert_manager

router = APIRouter(prefix="/dashboard", tags=["Dashboard Aggregation"])

@router.get("/health")
def get_dashboard_health(db: Session = Depends(get_db)):
    """Returns real-time health score, subsystem breakdown, and flight status."""
    records = db.query(TelemetryRecord).all()
    anomalies = db.query(AnomalyRecord).all()
    
    anom_dicts = [
        {
            "severity": a.severity, 
            "anomaly_type": a.anomaly_type, 
            "parameter": a.parameter,
            "timestamp": a.timestamp,
            "duration": a.duration or 0.0,
            "end_time": a.end_time,
            "confidence": a.confidence or 1.0
        }
        for a in anomalies
    ]
    
    if not records:
        return {"score": 100.0, "status": "NOMINAL", "total_records": 0, "anomalies_summary": {"critical": 0, "warning": 0, "info": 0}, "event_count": 0}
        
    df = pd.DataFrame([{"timestamp": r.timestamp} for r in records])
    health_info = alert_manager.calculate_system_health_score(df, anom_dicts)
    health_info["total_records"] = len(records)
    return health_info

@router.get("/physics-compliance")
def get_physics_compliance(db: Session = Depends(get_db)):
    """Returns per-relationship physics compliance breakdown with actual residuals."""
    records = db.query(TelemetryRecord).order_by(TelemetryRecord.timestamp.asc()).all()
    if not records:
        return alert_manager.calculate_physics_compliance(pd.DataFrame())
    
    data = []
    for r in records:
        d = {"timestamp": r.timestamp}
        for col in ["P_chamber", "T_chamber", "m_ox", "m_fuel", "F_thrust", "N_pump"]:
            d[col] = getattr(r, col)
        data.append(d)
    
    df = pd.DataFrame(data)
    return alert_manager.calculate_physics_compliance(df)

@router.get("/summary")
def get_dashboard_summary(db: Session = Depends(get_db)):
    """Returns aggregated summary data for all 7 dashboard panels."""
    telemetry_count = db.query(TelemetryRecord).count()
    anomaly_count = db.query(AnomalyRecord).count()
    imputation_count = db.query(ImputationRecord).count()
    
    # Calculate parameter correlations
    records = db.query(TelemetryRecord).order_by(TelemetryRecord.timestamp.asc()).all()
    corr_matrix = {}
    if records and len(records) > 10:
        data = []
        for r in records:
            data.append({
                "P_chamber": r.P_chamber,
                "T_chamber": r.T_chamber,
                "m_ox": r.m_ox,
                "m_fuel": r.m_fuel,
                "F_thrust": r.F_thrust,
                "N_pump": r.N_pump,
                "vib_x": r.vib_x,
                "acc_axial": r.acc_axial
            })
        df = pd.DataFrame(data).dropna()
        if not df.empty:
            corr_df = df.corr().fillna(0.0)
            corr_matrix = corr_df.to_dict()
            
    return {
        "telemetry_records": telemetry_count,
        "anomalies_detected": anomaly_count,
        "imputations_performed": imputation_count,
        "correlation_matrix": corr_matrix,
        "flight_duration_sec": 600.0
    }
