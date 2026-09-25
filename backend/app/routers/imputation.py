from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any
import pandas as pd
import numpy as np

from app.database import get_db
from app.models.telemetry import TelemetryRecord, ImputationRecord
from app.services.anomaly_detector import anomaly_service
from app.services.physics_imputer import physics_imputer

router = APIRouter(prefix="/imputation", tags=["Physics Imputation"])

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

@router.post("/run")
def run_physics_imputation(db: Session = Depends(get_db)):
    """Executes physics-constrained data imputation on missing/corrupted telemetry parameters."""
    records = db.query(TelemetryRecord).order_by(TelemetryRecord.timestamp.asc()).all()
    if not records:
        raise HTTPException(status_code=404, detail="No telemetry data found to perform imputation.")
        
    data = []
    for r in records:
        d = {"id": r.id, "timestamp": r.timestamp, "flight_phase": r.flight_phase}
        for col in ["P_chamber", "T_chamber", "m_ox", "m_fuel", "F_thrust", "N_pump", 
                    "P_tank_lox", "P_tank_fuel", "vib_x", "vib_y", "vib_z", 
                    "acc_axial", "v_batt", "i_bus", "T_skin", "rate_roll", "rate_pitch", "rate_yaw"]:
            d[col] = getattr(r, col)
        data.append(d)
        
    df = pd.DataFrame(data)
    
    # 1. Detect missing/corrupted anomalies
    anomalies = anomaly_service.detect_all_anomalies(df)
    
    # 2. Impute missing data with physics constraints
    df_imputed, imputation_records = physics_imputer.impute_telemetry_dataset(df, anomalies)
    
    # 3. Update database records
    db.query(ImputationRecord).delete()
    
    db_imp_objects = [
        ImputationRecord(
            timestamp=clean_float(imp["timestamp"]),
            parameter=str(imp["parameter"]),
            original_value=clean_float(imp["original_value"]),
            imputed_value=clean_float(imp["imputed_value"]) or 0.0,
            confidence_score=clean_float(imp["confidence_score"]) or 0.8,
            gap_duration=clean_float(imp["gap_duration"]) or 0.1,
            method_used=str(imp["method_used"]),
            physics_residual=clean_float(imp["physics_residual"])
        )
        for imp in imputation_records
    ]
    db.bulk_save_objects(db_imp_objects)
    
    # Fast in-memory update across pre-fetched DB records
    records_dict = {r.id: r for r in records}
    cols_to_update = ["P_chamber", "T_chamber", "m_ox", "m_fuel", "F_thrust", "N_pump", 
                      "P_tank_lox", "P_tank_fuel", "vib_x", "vib_y", "vib_z", 
                      "acc_axial", "v_batt", "i_bus", "T_skin", "rate_roll", "rate_pitch", "rate_yaw"]

    # Timestamps that ACTUALLY had a value imputed (from the imputation service's own
    # output), rounded for robust float comparison. Only these records should be
    # flagged is_imputed=True — NOT every record in the dataset.
    imputed_timestamps = {round(float(imp["timestamp"]), 6) for imp in imputation_records}

    for idx, row in df_imputed.iterrows():
        rec_id = int(row["id"])
        rec = records_dict.get(rec_id)
        if rec:
            for col in cols_to_update:
                if col in row and pd.notna(row[col]):
                    val = float(row[col])
                    if not (np.isnan(val) or np.isinf(val)):
                        setattr(rec, col, val)
            if round(float(row["timestamp"]), 6) in imputed_timestamps:
                rec.is_imputed = True
            
    db.commit()
    
    clean_summary = []
    for imp in imputation_records[:30]:
        c_imp = dict(imp)
        c_imp["original_value"] = clean_float(c_imp.get("original_value"))
        c_imp["imputed_value"] = clean_float(c_imp.get("imputed_value"))
        c_imp["confidence_score"] = clean_float(c_imp.get("confidence_score"))
        c_imp["physics_residual"] = clean_float(c_imp.get("physics_residual"))
        clean_summary.append(c_imp)
        
    return {
        "status": "success",
        "total_imputed_points": len(imputation_records),
        "imputation_summary": clean_summary
    }

@router.get("/results")
def get_imputation_results(db: Session = Depends(get_db)):
    """Returns all recorded physics imputation results and confidence metrics."""
    records = db.query(ImputationRecord).order_by(ImputationRecord.timestamp.asc()).all()
    return [
        {
            "id": r.id,
            "timestamp": clean_float(r.timestamp),
            "parameter": r.parameter,
            "original_value": clean_float(r.original_value),
            "imputed_value": clean_float(r.imputed_value),
            "confidence_score": clean_float(r.confidence_score),
            "gap_duration": clean_float(r.gap_duration),
            "method_used": r.method_used,
            "physics_residual": clean_float(r.physics_residual)
        }
        for r in records
    ]
