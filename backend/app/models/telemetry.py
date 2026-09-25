from sqlalchemy import Column, Integer, Float, String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

class TelemetryRecord(Base):
    __tablename__ = "telemetry_records"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(Float, index=True, nullable=False)  # Mission time T+ seconds (0 to 600.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 16 Core Telemetry Parameters
    P_chamber = Column(Float, nullable=True)     # Chamber Pressure (MPa)
    T_chamber = Column(Float, nullable=True)     # Chamber Temp (K)
    m_ox = Column(Float, nullable=True)          # Oxidizer Flow Rate (kg/s)
    m_fuel = Column(Float, nullable=True)        # Fuel Flow Rate (kg/s)
    F_thrust = Column(Float, nullable=True)      # Thrust (kN)
    N_pump = Column(Float, nullable=True)        # Turbopump Speed (RPM)
    P_tank_lox = Column(Float, nullable=True)    # Tank Pressure LOX (MPa)
    P_tank_fuel = Column(Float, nullable=True)   # Tank Pressure Fuel (MPa)
    vib_x = Column(Float, nullable=True)         # Vibration X (g)
    vib_y = Column(Float, nullable=True)         # Vibration Y (g)
    vib_z = Column(Float, nullable=True)         # Vibration Z (g)
    acc_axial = Column(Float, nullable=True)     # Acceleration Axial (g)
    v_batt = Column(Float, nullable=True)        # Battery Voltage (V)
    i_bus = Column(Float, nullable=True)         # Bus Current (A)
    T_skin = Column(Float, nullable=True)        # Skin Temp (K)
    rate_roll = Column(Float, nullable=True)     # Roll Rate (deg/s)
    rate_pitch = Column(Float, nullable=True)    # Pitch Rate (deg/s)
    rate_yaw = Column(Float, nullable=True)      # Yaw Rate (deg/s)

    flight_phase = Column(String, default="PRE_LAUNCH")
    is_imputed = Column(Boolean, default=False)

class ImputationRecord(Base):
    __tablename__ = "imputation_records"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(Float, index=True, nullable=False)
    parameter = Column(String, nullable=False, index=True)
    original_value = Column(Float, nullable=True)
    imputed_value = Column(Float, nullable=False)
    confidence_score = Column(Float, nullable=False)  # 0.0 to 1.0
    gap_duration = Column(Float, nullable=False)       # seconds
    method_used = Column(String, nullable=False)      # spline / PINN / ensemble
    physics_residual = Column(Float, nullable=True)
