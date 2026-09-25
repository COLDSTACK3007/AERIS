from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, WebSocket, WebSocketDisconnect, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
import pandas as pd
import numpy as np

from app.database import get_db
from app.models.telemetry import TelemetryRecord, ImputationRecord
from app.models.anomaly import AnomalyRecord
from app.models.alert import AlertRecord
from app.services.ingestion import ingestion_service
from app.services.synthetic_data import PARAM_METADATA
from app.websocket.manager import ws_manager

router = APIRouter(prefix="/telemetry", tags=["Telemetry"])

@router.get("/parameters")
def get_parameter_metadata():
    """Returns metadata for all 16 launch vehicle telemetry parameters."""
    return PARAM_METADATA

@router.post("/upload")
async def upload_telemetry_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Uploads CSV file, normalizes, resamples, and persists telemetry to database."""
    if not file.filename.lower().endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV (.csv)")
    
    content = await file.read()
    try:
        df_raw = ingestion_service.parse_csv_telemetry(content)
        df = ingestion_service.resample_multi_rate_data(df_raw)
        
        # Valid TelemetryRecord columns
        valid_cols = {c.name for c in TelemetryRecord.__table__.columns} - {'id', 'created_at'}
        
        # Save records to DB
        records = []
        for _, row in df.iterrows():
            rec_dict = row.to_dict()
            clean_dict = {}
            for k, v in rec_dict.items():
                if k in valid_cols:
                    if pd.isna(v) or (isinstance(v, float) and (np.isnan(v) or np.isinf(v))):
                        clean_dict[k] = None
                    else:
                        clean_dict[k] = v
            rec = TelemetryRecord(**clean_dict)
            records.append(rec)
            
        # Replace current run telemetry and reset downstream anomaly/imputation/alert records
        db.query(TelemetryRecord).delete()
        db.query(AnomalyRecord).delete()
        db.query(ImputationRecord).delete()
        db.query(AlertRecord).delete()
        
        db.bulk_save_objects(records)
        db.commit()

        if ws_manager.active_connections:
            for rec in records:
                rec_dict = {
                    c.name: getattr(rec, c.name, None)
                    for c in TelemetryRecord.__table__.columns if c.name not in {'id', 'created_at'}
                }
                clean_dict = {k: (None if (isinstance(v, float) and (np.isnan(v) or np.isinf(v))) else v) for k, v in rec_dict.items()}
                await ws_manager.broadcast(clean_dict)
        
        min_t = float(df["timestamp"].min()) if not df.empty else 0.0
        max_t = float(df["timestamp"].max()) if not df.empty else 0.0
        
        return {
            "status": "success",
            "filename": file.filename,
            "rows_ingested": len(records),
            "time_range": [min_t, max_t]
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to process CSV: {str(e)}")

@router.get("/data")
def get_telemetry_data(
    start_time: Optional[float] = Query(None),
    end_time: Optional[float] = Query(None),
    parameters: Optional[List[str]] = Query(None),
    db: Session = Depends(get_db)
):
    """Queries telemetry data within time bounds and selected parameters."""
    query = db.query(TelemetryRecord)
    if start_time is not None:
        query = query.filter(TelemetryRecord.timestamp >= start_time)
    if end_time is not None:
        query = query.filter(TelemetryRecord.timestamp <= end_time)
        
    records = query.order_by(TelemetryRecord.timestamp.asc()).all()
    
    if parameters:
        actual_params = []
        for p in parameters:
            actual_params.extend([item.strip() for item in p.split(",") if item.strip()])
        param_list = actual_params
    else:
        param_list = list(PARAM_METADATA.keys())

    result = []
    for r in records:
        d = {
            "id": r.id,
            "timestamp": r.timestamp,
            "flight_phase": r.flight_phase,
            "is_imputed": r.is_imputed
        }
        for p in param_list:
            if hasattr(r, p):
                val = getattr(r, p)
                if val is not None and isinstance(val, float) and (np.isnan(val) or np.isinf(val)):
                    d[p] = None
                else:
                    d[p] = val
        result.append(d)
        
    return result

@router.websocket("/stream")
async def telemetry_websocket(websocket: WebSocket):
    """WebSocket endpoint for real-time dashboard telemetry updates."""
    await ws_manager.connect(websocket)
    try:
        while True:
            # Keep connection alive & receive optional control frames
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
