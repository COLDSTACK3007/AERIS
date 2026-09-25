from sqlalchemy import Column, Integer, Float, String, DateTime, Text
from datetime import datetime
from app.database import Base

class AnomalyRecord(Base):
    __tablename__ = "anomaly_records"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(Float, index=True, nullable=False)
    parameter = Column(String, nullable=False, index=True)
    anomaly_type = Column(String, nullable=False)  # GAP, DRIFT, NOISE, STUCK, SPIKE
    severity = Column(String, default="WARNING")     # INFO, WARNING, CRITICAL
    description = Column(Text, nullable=True)
    value_observed = Column(Float, nullable=True)
    expected_range_min = Column(Float, nullable=True)
    expected_range_max = Column(Float, nullable=True)
    flight_phase = Column(String, nullable=True)
    duration = Column(Float, nullable=True, default=0.0)
    end_time = Column(Float, nullable=True)
    confidence = Column(Float, default=1.0)
    created_at = Column(DateTime, default=datetime.utcnow)
