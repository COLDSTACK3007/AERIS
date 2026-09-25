from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any
import pandas as pd

from app.database import get_db
from app.models.alert import AlertRecord
from app.models.anomaly import AnomalyRecord
from app.models.telemetry import TelemetryRecord
from app.services.alert_manager import alert_manager

router = APIRouter(prefix="/alerts", tags=["Alerts & Reporting"])

@router.get("")
def get_all_alerts(db: Session = Depends(get_db)):
    """Returns live and historical alerts."""
    alerts = db.query(AlertRecord).order_by(AlertRecord.timestamp.desc()).all()
    
    if not alerts:
        anomalies_recs = db.query(AnomalyRecord).order_by(AnomalyRecord.timestamp.asc()).all()
        if anomalies_recs:
            anoms = [
                {
                    "timestamp": a.timestamp,
                    "parameter": a.parameter,
                    "anomaly_type": a.anomaly_type,
                    "severity": a.severity,
                    "description": a.description,
                    "value_observed": a.value_observed
                }
                for a in anomalies_recs
            ]
            alert_objs = alert_manager.generate_alerts_from_anomalies(anoms)
            db_alerts = [
                AlertRecord(
                    timestamp=alt["timestamp"],
                    level=alt["level"],
                    title=alt["title"],
                    message=alt["message"],
                    parameter=alt.get("parameter", "UNKNOWN"),
                    is_acknowledged=False
                )
                for alt in alert_objs
            ]
            db.bulk_save_objects(db_alerts)
            db.commit()
            alerts = db.query(AlertRecord).order_by(AlertRecord.timestamp.desc()).all()

    return [
        {
            "id": a.id,
            "timestamp": a.timestamp,
            "level": a.level,
            "title": a.title,
            "message": a.message,
            "parameter": a.parameter,
            "is_acknowledged": a.is_acknowledged,
            "created_at": a.created_at.isoformat() if a.created_at else None
        }
        for a in alerts
    ]

@router.post("/acknowledge/{alert_id}")
def acknowledge_alert(alert_id: int, db: Session = Depends(get_db)):
    """Acknowledges an alert by ID."""
    alert = db.query(AlertRecord).filter(AlertRecord.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.is_acknowledged = True
    db.commit()
    return {"status": "success", "message": f"Alert {alert_id} acknowledged."}

@router.post("/reports/generate")
def generate_flight_report(db: Session = Depends(get_db)):
    """Generates comprehensive PDF/JSON flight analysis report."""
    telemetry_recs = db.query(TelemetryRecord).all()
    anomalies_recs = db.query(AnomalyRecord).all()
    alerts_recs = db.query(AlertRecord).all()
    
    data = []
    for r in telemetry_recs:
        d = {"timestamp": r.timestamp}
        for col in ["P_chamber", "T_chamber", "m_ox", "m_fuel", "F_thrust", 
                    "N_pump", "P_tank_lox", "P_tank_fuel", "vib_x", "vib_y", 
                    "vib_z", "acc_axial", "v_batt", "i_bus", "T_skin", 
                    "rate_roll", "rate_pitch", "rate_yaw"]:
            d[col] = getattr(r, col, None)
        data.append(d)
    df = pd.DataFrame(data) if data else pd.DataFrame()
    
    anomalies = [
        {
            "timestamp": a.timestamp,
            "parameter": a.parameter,
            "anomaly_type": a.anomaly_type,
            "severity": a.severity,
            "description": a.description,
            "value_observed": a.value_observed,
            "flight_phase": a.flight_phase
        }
        for a in anomalies_recs
    ]
    
    alerts = [
        {
            "id": a.id,
            "timestamp": a.timestamp,
            "level": a.level,
            "title": a.title,
            "message": a.message,
            "parameter": a.parameter,
            "is_acknowledged": a.is_acknowledged
        }
        for a in alerts_recs
    ]
    
    report = alert_manager.generate_comprehensive_flight_report(df, anomalies, alerts)
    return report
