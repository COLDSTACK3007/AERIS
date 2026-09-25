from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
import pandas as pd
import numpy as np

from app.config import settings
from app.database import engine, Base, SessionLocal
from app.routers import telemetry, synthetic, anomaly, imputation, alerts, dashboard, analysis
from app.models.telemetry import TelemetryRecord
from app.services.synthetic_data import generate_synthetic_telemetry

from app.models.anomaly import AnomalyRecord
from app.models.alert import AlertRecord
from app.services.anomaly_detector import anomaly_service
from app.services.alert_manager import alert_manager

from sqlalchemy import inspect, text

# Create DB tables & ensure schema migration for anomaly_records
try:
    Base.metadata.create_all(bind=engine)
    with engine.connect() as conn:
        if inspect(engine).has_table('anomaly_records'):
            existing_cols = [col['name'] for col in inspect(engine).get_columns('anomaly_records')]
            if 'duration' not in existing_cols:
                conn.execute(text("ALTER TABLE anomaly_records ADD COLUMN duration FLOAT DEFAULT 0.0"))
            if 'end_time' not in existing_cols:
                conn.execute(text("ALTER TABLE anomaly_records ADD COLUMN end_time FLOAT"))
            conn.commit()
except Exception as e:
    print(f"DB table creation / migration warning: {e}")

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Config - allow local frontend and Vercel deployments
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Routers (with /api prefix)
app.include_router(telemetry.router, prefix=settings.API_V1_STR)
app.include_router(synthetic.router, prefix=settings.API_V1_STR)
app.include_router(anomaly.router, prefix=settings.API_V1_STR)
app.include_router(imputation.router, prefix=settings.API_V1_STR)
app.include_router(alerts.router, prefix=settings.API_V1_STR)
app.include_router(dashboard.router, prefix=settings.API_V1_STR)
app.include_router(analysis.router, prefix=settings.API_V1_STR)

# Also mount without /api prefix (for Vercel serverless function rewrites that strip /api)
app.include_router(telemetry.router)
app.include_router(synthetic.router)
app.include_router(anomaly.router)
app.include_router(imputation.router)
app.include_router(alerts.router)
app.include_router(dashboard.router)
app.include_router(analysis.router)

@app.on_event("startup")
def auto_populate_synthetic_data_if_empty():
    """Auto-generates synthetic telemetry dataset, anomalies, and alerts on startup if DB is fresh."""
    try:
        db = SessionLocal()
        try:
            count = db.query(TelemetryRecord).count()
            if count == 0:
                print("Database empty. Auto-generating synthetic launch telemetry dataset...")
                df = generate_synthetic_telemetry(duration=600.0, dt=2.0, inject_anomalies=True)
                records = []
                for _, row in df.iterrows():
                    rec_dict = row.to_dict()
                    clean_dict = {k: (None if (isinstance(v, float) and (pd.isna(v) or np.isnan(v) or np.isinf(v))) else v) for k, v in rec_dict.items()}
                    records.append(TelemetryRecord(**clean_dict))
                db.bulk_save_objects(records)

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
                    flight_phase=str(a.get("flight_phase", "UNKNOWN"))
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
            print(f"Successfully auto-generated {len(records)} initial telemetry records, {len(anomalies)} anomalies, and {len(alert_objs)} priority alerts.")
        except Exception as e:
            print(f"Startup synthetic data generation warning: {e}")
            db.rollback()
        finally:
            db.close()
    except Exception as outer_e:
        print(f"Database connection startup warning: {outer_e}")

@app.get("/")
def root_endpoint():
    return {
        "project": "AERIS — Physics-Constrained Telemetry Framework",
        "organization": "ISRO / SIH2026170",
        "status": "online",
        "docs": "/docs"
    }
