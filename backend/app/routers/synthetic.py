from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
import pandas as pd
import numpy as np

from app.database import get_db
from app.models.telemetry import TelemetryRecord, ImputationRecord
from app.models.anomaly import AnomalyRecord
from app.models.alert import AlertRecord
from app.services.synthetic_data import generate_synthetic_telemetry
from app.services.anomaly_detector import anomaly_service
from app.services.alert_manager import alert_manager
from app.websocket.manager import ws_manager

router = APIRouter(prefix="/synthetic", tags=["Synthetic Data"])

@router.post("/generate")
async def generate_and_load_synthetic_data(
    duration: float = Query(600.0, description="Mission duration in seconds"),
    dt: float = Query(0.1, description="Sampling time step in seconds"),
    inject_anomalies: bool = Query(True, description="Whether to inject synthetic gaps and sensor faults"),
    db: Session = Depends(get_db)
):
    """Generates synthetic 600-second launch vehicle telemetry and populates the database."""
    try:
        df = generate_synthetic_telemetry(duration=duration, dt=dt, inject_anomalies=inject_anomalies)
        
        # Clear existing dataset and reset downstream records
        db.query(TelemetryRecord).delete()
        db.query(AnomalyRecord).delete()
        db.query(ImputationRecord).delete()
        db.query(AlertRecord).delete()
        
        records = []
        for _, row in df.iterrows():
            rec_dict = row.to_dict()
            clean_dict = {k: (None if (isinstance(v, float) and np.isnan(v)) else v) for k, v in rec_dict.items()}
            records.append(TelemetryRecord(**clean_dict))
            
        db.bulk_save_objects(records)
        
        # Auto-detect anomalies and generate priority alerts if injected
        if inject_anomalies:
            anomalies = anomaly_service.detect_all_anomalies(df)
            db_anomalies = [
                AnomalyRecord(
                    timestamp=a["timestamp"],
                    parameter=str(a["parameter"]),
                    anomaly_type=str(a["anomaly_type"]),
                    severity=str(a["severity"]),
                    description=str(a["description"]),
                    value_observed=a.get("value_observed"),
                    expected_range_min=a.get("expected_range_min"),
                    expected_range_max=a.get("expected_range_max"),
                    confidence=a.get("confidence", 1.0) or 1.0,
                    flight_phase=str(a.get("flight_phase", "UNKNOWN")),
                    duration=a.get("duration", 0.0) or 0.0,
                    end_time=a.get("end_time")
                )
                for a in anomalies
            ]
            db.bulk_save_objects(db_anomalies)
            
            alert_objs = alert_manager.generate_alerts_from_anomalies(anomalies)
            db_alerts = [
                AlertRecord(
                    timestamp=alt["timestamp"],
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

        # Broadcast records to active websocket clients
        if ws_manager.active_connections:
            for rec in records:
                rec_dict = {
                    c.name: getattr(rec, c.name, None)
                    for c in TelemetryRecord.__table__.columns if c.name not in {'id', 'created_at'}
                }
                clean_dict = {k: (None if (isinstance(v, float) and (np.isnan(v) or np.isinf(v))) else v) for k, v in rec_dict.items()}
                await ws_manager.broadcast(clean_dict)

        
        return {
            "status": "success",
            "message": f"Generated {len(records)} telemetry records across {duration} seconds.",
            "duration": duration,
            "anomalies_injected": inject_anomalies,
            "total_records": len(records)
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Synthetic generation failed: {str(e)}")
