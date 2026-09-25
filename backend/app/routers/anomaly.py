from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any
import pandas as pd
import numpy as np

from app.database import get_db
from app.models.telemetry import TelemetryRecord
from app.models.anomaly import AnomalyRecord
from app.models.alert import AlertRecord
from app.services.anomaly_detector import anomaly_service
from app.services.alert_manager import alert_manager

router = APIRouter(prefix="/anomaly", tags=["Anomaly Detection"])

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

@router.post("/detect")
def run_anomaly_detection(db: Session = Depends(get_db)):
    """Runs anomaly detection across all telemetry records in the database."""
    records = db.query(TelemetryRecord).order_by(TelemetryRecord.timestamp.asc()).all()
    if not records:
        raise HTTPException(status_code=404, detail="No telemetry data found in database to scan.")
        
    data = []
    for r in records:
        d = {"id": r.id, "timestamp": r.timestamp, "flight_phase": r.flight_phase}
        for col in ["P_chamber", "T_chamber", "m_ox", "m_fuel", "F_thrust", "N_pump", 
                    "P_tank_lox", "P_tank_fuel", "vib_x", "vib_y", "vib_z", 
                    "acc_axial", "v_batt", "i_bus", "T_skin", "rate_roll", "rate_pitch", "rate_yaw"]:
            d[col] = getattr(r, col)
        data.append(d)
        
    df = pd.DataFrame(data)
    anomalies = anomaly_service.detect_all_anomalies(df)
    
    # Store anomaly records in database
    db.query(AnomalyRecord).delete()
    db_anomalies = [
        AnomalyRecord(
            timestamp=clean_float(a["timestamp"]),
            parameter=str(a["parameter"]),
            anomaly_type=str(a["anomaly_type"]),
            severity=str(a["severity"]),
            description=str(a["description"]),
            value_observed=clean_float(a.get("value_observed")),
            expected_range_min=clean_float(a.get("expected_range_min")),
            expected_range_max=clean_float(a.get("expected_range_max")),
            confidence=clean_float(a.get("confidence", 1.0)) or 1.0,
            flight_phase=str(a.get("flight_phase", "UNKNOWN")),
            duration=clean_float(a.get("duration", 0.0)) or 0.0,
            end_time=clean_float(a.get("end_time"))
        )
        for a in anomalies
    ]
    db.bulk_save_objects(db_anomalies)

    # Store priority alert records in database
    db.query(AlertRecord).delete()
    alert_objs = alert_manager.generate_alerts_from_anomalies(anomalies)
    db_alerts = [
        AlertRecord(
            timestamp=clean_float(alt["timestamp"]),
            level=str(alt["level"]),
            title=str(alt["title"]),
            message=str(alt["message"]),
            parameter=str(alt.get("parameter", "UNKNOWN")),
            is_acknowledged=False
        )
        for alt in alert_objs
    ]
    db.bulk_save_objects(db_alerts)

    db.commit()
    
    clean_preview = []
    for a in anomalies[:50]:
        ca = dict(a)
        ca["timestamp"] = clean_float(ca.get("timestamp"))
        ca["value_observed"] = clean_float(ca.get("value_observed"))
        ca["expected_range_min"] = clean_float(ca.get("expected_range_min"))
        ca["expected_range_max"] = clean_float(ca.get("expected_range_max"))
        ca["confidence"] = clean_float(ca.get("confidence")) or 1.0
        ca["duration"] = clean_float(ca.get("duration", 0.0)) or 0.0
        ca["end_time"] = clean_float(ca.get("end_time"))
        clean_preview.append(ca)

    return {
        "status": "success",
        "total_anomalies_detected": len(anomalies),
        "anomalies": clean_preview
    }

@router.get("/results")
def get_anomaly_results(db: Session = Depends(get_db)):
    """Returns stored anomaly detection records."""
    records = db.query(AnomalyRecord).order_by(AnomalyRecord.timestamp.asc()).all()
    return [
        {
            "id": r.id,
            "timestamp": clean_float(r.timestamp),
            "parameter": r.parameter,
            "anomaly_type": r.anomaly_type,
            "severity": r.severity,
            "description": r.description,
            "value_observed": clean_float(r.value_observed),
            "expected_range_min": clean_float(r.expected_range_min),
            "expected_range_max": clean_float(r.expected_range_max),
            "confidence": clean_float(r.confidence) or 1.0,
            "flight_phase": r.flight_phase,
            "duration": clean_float(r.duration) or 0.0,
            "end_time": clean_float(r.end_time),
            "created_at": r.created_at.isoformat() if r.created_at else None
        }
        for r in records
    ]
