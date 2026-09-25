from sqlalchemy import Column, Integer, Float, String, DateTime, Boolean, Text
from datetime import datetime
from app.database import Base

class AlertRecord(Base):
    __tablename__ = "alert_records"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(Float, nullable=False)
    level = Column(String, nullable=False)  # INFO, WARNING, CRITICAL
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    parameter = Column(String, nullable=True)
    is_acknowledged = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
