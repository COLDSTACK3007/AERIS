import numpy as np
import pandas as pd
from typing import Dict, List, Optional

# =============================================================================
# PARAMETER METADATA — Authoritative ranges for all 16 telemetry parameters
# Units: Pressure→MPa, Thrust→kN, Mass flow→kg/s, Temperature→K,
#         Acceleration→g, RPM→RPM, Voltage→V, Current→A, Time→s
# =============================================================================
PARAM_METADATA = {
    "P_chamber": {"unit": "MPa", "min": 0.0, "max": 8.0, "nominal": 6.22, "rate": 100},
    "T_chamber": {"unit": "K", "min": 280.0, "max": 3600.0, "nominal": 3200.0, "rate": 100},
    "m_ox": {"unit": "kg/s", "min": 0.0, "max": 300.0, "nominal": 240.0, "rate": 50},
    "m_fuel": {"unit": "kg/s", "min": 0.0, "max": 120.0, "nominal": 96.0, "rate": 50},
    "F_thrust": {"unit": "kN", "min": 0.0, "max": 1100.0, "nominal": 972.0, "rate": 100},
    "N_pump": {"unit": "RPM", "min": 0.0, "max": 42000.0, "nominal": 34944.0, "rate": 200},
    "P_tank_lox": {"unit": "MPa", "min": 0.0, "max": 5.0, "nominal": 4.2, "rate": 10},
    "P_tank_fuel": {"unit": "MPa", "min": 0.0, "max": 4.0, "nominal": 3.5, "rate": 10},
    "vib_x": {"unit": "g", "min": -20.0, "max": 20.0, "nominal": 0.5, "rate": 1000},
    "vib_y": {"unit": "g", "min": -20.0, "max": 20.0, "nominal": 0.5, "rate": 1000},
    "vib_z": {"unit": "g", "min": -20.0, "max": 20.0, "nominal": 0.5, "rate": 1000},
    "acc_axial": {"unit": "g", "min": 0.0, "max": 12.0, "nominal": 1.2, "rate": 100},
    "v_batt": {"unit": "V", "min": 22.0, "max": 32.0, "nominal": 28.0, "rate": 1},
    "i_bus": {"unit": "A", "min": 0.0, "max": 50.0, "nominal": 18.0, "rate": 1},
    "T_skin": {"unit": "K", "min": 200.0, "max": 2000.0, "nominal": 450.0, "rate": 10},
    "rate_roll": {"unit": "deg/s", "min": -5.0, "max": 5.0, "nominal": 0.0, "rate": 50},
    "rate_pitch": {"unit": "deg/s", "min": -3.0, "max": 3.0, "nominal": 0.0, "rate": 50},
    "rate_yaw": {"unit": "deg/s", "min": -3.0, "max": 3.0, "nominal": 0.0, "rate": 50}
}

# =============================================================================
# PHYSICS CONSTANTS & AUTHORITATIVE TOLERANCES — Single source of truth
# =============================================================================
ISP = 295.0           # Specific impulse (seconds)
G0 = 9.81             # Standard gravity (m/s²)
K_CHAMBER = 0.0185    # Simplified chamber pressure coefficient: P = k * (m_ox + m_fuel)
NOMINAL_M_OX = 240.0  # Stage-1 nominal oxidizer flow (kg/s)
NOMINAL_M_FUEL = 96.0  # Stage-1 nominal fuel flow (kg/s)
NOMINAL_THRUST_KN = (NOMINAL_M_OX + NOMINAL_M_FUEL) * ISP * G0 / 1000.0  # ≈ 972.3 kN
OF_RATIO_NOMINAL = NOMINAL_M_OX / NOMINAL_M_FUEL  # 2.5
OF_RATIO_MIN = 1.8
OF_RATIO_MAX = 3.2

# Engineering-motivated physics tolerance constants
THRUST_TOLERANCE_KN = 15.0       # Acceptable thrust residual (kN)
PRESSURE_TOLERANCE_MPA = 0.3     # Acceptable chamber pressure residual (MPa)
MASS_FLOW_TOLERANCE_KGS = 5.0    # Acceptable mass flow residual (kg/s)
TEMPERATURE_TOLERANCE_K = 50.0   # Acceptable chamber temperature residual (K)
OF_RATIO_TOLERANCE = 0.5         # Acceptable O/F ratio deviation from nominal 2.5
PUMP_SPEED_TOLERANCE_RPM = 1000.0 # RPM
TANK_PRESSURE_TOLERANCE_MPA = 0.2 # MPa
VOLTAGE_TOLERANCE_V = 0.5        # V
CURRENT_TOLERANCE_A = 2.0        # A
SKIN_TEMP_TOLERANCE_K = 20.0     # K
VIBRATION_TOLERANCE_G = 2.0      # g
ACCEL_TOLERANCE_G = 0.5          # g
ANGULAR_RATE_TOLERANCE_DEG = 0.5 # deg/s

RESIDUAL_TOLERANCES = {
    "F_thrust": THRUST_TOLERANCE_KN,
    "P_chamber": PRESSURE_TOLERANCE_MPA,
    "T_chamber": TEMPERATURE_TOLERANCE_K,
    "m_ox": MASS_FLOW_TOLERANCE_KGS,
    "m_fuel": 2.0,
    "N_pump": PUMP_SPEED_TOLERANCE_RPM,
    "P_tank_lox": TANK_PRESSURE_TOLERANCE_MPA,
    "P_tank_fuel": TANK_PRESSURE_TOLERANCE_MPA,
    "v_batt": VOLTAGE_TOLERANCE_V,
    "i_bus": CURRENT_TOLERANCE_A,
    "T_skin": SKIN_TEMP_TOLERANCE_K,
    "vib_x": VIBRATION_TOLERANCE_G,
    "vib_y": VIBRATION_TOLERANCE_G,
    "vib_z": VIBRATION_TOLERANCE_G,
    "acc_axial": ACCEL_TOLERANCE_G,
    "rate_roll": ANGULAR_RATE_TOLERANCE_DEG,
    "rate_pitch": 0.3,
    "rate_yaw": 0.3,
}


# =============================================================================
# PHASE-DEPENDENT EXPECTED RANGES — For phase-aware anomaly detection
# Each phase defines expected nominal ranges for key parameters.
# =============================================================================
PHASE_EXPECTED_RANGES = {
    "PRE_LAUNCH": {
        "F_thrust": (0.0, 5.0),
        "m_ox": (0.0, 2.0),
        "m_fuel": (0.0, 1.0),
        "P_chamber": (0.0, 0.2),
        "T_chamber": (280.0, 320.0),
        "N_pump": (0.0, 500.0),
        "v_batt": (26.0, 30.0),
    },
    "LIFTOFF": {
        "F_thrust": (0.0, 1050.0),
        "m_ox": (0.0, 260.0),
        "m_fuel": (0.0, 105.0),
        "P_chamber": (0.0, 7.5),
        "T_chamber": (280.0, 3500.0),
        "N_pump": (0.0, 40000.0),
        "v_batt": (25.0, 30.0),
    },
    "MAX_Q": {
        "F_thrust": (800.0, 1050.0),
        "m_ox": (200.0, 260.0),
        "m_fuel": (80.0, 105.0),
        "P_chamber": (5.0, 7.5),
        "T_chamber": (2800.0, 3500.0),
        "N_pump": (28000.0, 40000.0),
        "v_batt": (25.0, 30.0),
    },
    "STAGE_1_FLIGHT": {
        "F_thrust": (800.0, 1050.0),
        "m_ox": (200.0, 260.0),
        "m_fuel": (80.0, 105.0),
        "P_chamber": (5.0, 7.5),
        "T_chamber": (2800.0, 3500.0),
        "N_pump": (28000.0, 40000.0),
        "v_batt": (25.0, 30.0),
    },
    "STAGE_SEPARATION": {
        "F_thrust": (0.0, 50.0),
        "m_ox": (0.0, 10.0),
        "m_fuel": (0.0, 5.0),
        "P_chamber": (0.0, 1.0),
        "T_chamber": (280.0, 3500.0),
        "N_pump": (0.0, 5000.0),
        "v_batt": (24.0, 30.0),
    },
    "STAGE_2_FLIGHT": {
        "F_thrust": (500.0, 850.0),
        "m_ox": (140.0, 200.0),
        "m_fuel": (55.0, 80.0),
        "P_chamber": (3.0, 6.0),
        "T_chamber": (2500.0, 3400.0),
        "N_pump": (18000.0, 32000.0),
        "v_batt": (24.0, 29.0),
    },
    "COAST_ORBIT": {
        "F_thrust": (0.0, 2.0),
        "m_ox": (0.0, 2.0),
        "m_fuel": (0.0, 1.0),
        "P_chamber": (0.0, 0.2),
        "T_chamber": (280.0, 350.0),
        "N_pump": (0.0, 500.0),
        "v_batt": (23.0, 29.0),
    },
}

# Phase transition boundary times (seconds)
PHASE_BOUNDARIES = [10.0, 60.0, 90.0, 150.0, 160.0, 450.0]

# =============================================================================
# INJECTED ANOMALY MANIFEST — Documents what faults are intentionally injected
# Used by tests to verify detection
# =============================================================================
INJECTED_ANOMALIES = [
    {"type": "GAP", "parameter": "P_chamber", "start": 120.0, "end": 123.0, "description": "Short NaN gap in P_chamber"},
    {"type": "GAP", "parameter": "m_ox", "start": 250.0, "end": 258.0, "description": "Long NaN gap in m_ox"},
    {"type": "DRIFT", "parameter": "P_tank_lox", "start": 200.0, "end": 240.0, "description": "Gradual +1.2 MPa drift in P_tank_lox"},
    {"type": "NOISE", "parameter": "vib_x", "start": 300.0, "end": 330.0, "description": "High-frequency noise injection in vib_x"},
    {"type": "STUCK", "parameter": "v_batt", "start": 180.0, "end": 210.0, "description": "Battery voltage stuck at 27.4V"},
    {"type": "SPIKE", "parameter": "T_skin", "start": 379.8, "end": 380.2, "description": "Transient +450K spike in T_skin"},
]


def determine_flight_phase(t: float) -> str:
    """Determines flight phase from mission elapsed time (MET)."""
    if t <= 10.0:
        return "PRE_LAUNCH"
    elif 10.0 < t <= 60.0:
        return "LIFTOFF"
    elif 60.0 < t <= 90.0:
        return "MAX_Q"
    elif 90.0 < t <= 150.0:
        return "STAGE_1_FLIGHT"
    elif 150.0 < t <= 160.0:
        return "STAGE_SEPARATION"
    elif 160.0 < t <= 450.0:
        return "STAGE_2_FLIGHT"
    else:
        return "COAST_ORBIT"


def is_phase_transition(t: float, margin: float = 3.0) -> bool:
    """Returns True if timestamp is within 'margin' seconds of a phase boundary."""
    for boundary in PHASE_BOUNDARIES:
        if abs(t - boundary) <= margin:
            return True
    return False


def generate_synthetic_telemetry(
    duration: float = 600.0, 
    dt: float = 0.1, 
    inject_anomalies: bool = True,
    random_seed: Optional[int] = None
) -> pd.DataFrame:
    """Generates a physics-consistent flight profile with 16 telemetry parameters.
    
    Physics model:
        F_thrust = (m_ox + m_fuel) * Isp * g0 / 1000  [kN]
        P_chamber = k * (m_ox + m_fuel)                [MPa]  (simplified empirical relationship)
        N_pump = 104 * (m_ox + m_fuel)                 [RPM]  (proportional to total flow)
        acc_axial = F_thrust*1000 / (mass * g0)        [g]
    """
    if random_seed is not None:
        np.random.seed(random_seed)
    
    t_series = np.arange(0, duration, dt)
    n_points = len(t_series)
    
    # Initialize base data container
    data = {"timestamp": t_series, "flight_phase": [determine_flight_phase(t) for t in t_series]}
    
    # -------------------------------------------------------------------------
    # Rocket mass profile: initial 100,000 kg, propellant burns down
    # Stage-1 burn rate ~336 kg/s for 150s, Stage-2 burn rate ~252 kg/s for 290s
    # -------------------------------------------------------------------------
    mass = np.maximum(
        20000.0, 
        100000.0 - 500.0 * np.minimum(t_series, 150) 
        - 150.0 * np.maximum(0, np.minimum(t_series - 160, 290))
    )
    
    # -------------------------------------------------------------------------
    # Throttle profile — REALISTIC ROCKET PROPULSION PROFILE
    # PRE_LAUNCH (T≤10s): throttle=0 (no engine firing)
    # LIFTOFF ignition ramp (10-15s): throttle 0→1 over 5 seconds
    # MAX_Q throttle bucket (60-90s): throttle dips down to 0.78 for aerodynamic load relief
    # Stage-1 flight (15-150s): throttle=1.0 (except Max-Q bucket)
    # Stage separation (150-160s): throttle=0.0 (engine shutdown & tail-off)
    # Stage-2 flight (160-450s): throttle=0.75
    # Coast/orbit (>450s): throttle=0.0
    # -------------------------------------------------------------------------
    # Max-Q throttle bucket dip centered at T=75s
    max_q_bucket = 0.22 * np.exp(-((t_series - 75.0) ** 2) / 100.0)

    base_throttle = np.where(
        t_series <= 10.0, 0.0,                               # PRE_LAUNCH: engines off
        np.where(t_series <= 15.0, (t_series - 10.0) / 5.0,   # Ignition ramp
        np.where(t_series <= 150.0, 1.0 - max_q_bucket,      # Stage-1 with Max-Q bucket
        np.where(t_series <= 160.0, np.maximum(0.0, (160.0 - t_series) / 10.0 * 0.1), # Shutdown tail-off
        np.where(t_series <= 450.0, 0.75,                    # Stage-2 flight
        0.0)))))                                              # Coast

    throttle = np.clip(base_throttle, 0.0, 1.0)
    
    # -------------------------------------------------------------------------
    # Flow rates (kg/s) — derived from throttle
    # -------------------------------------------------------------------------
    m_ox = NOMINAL_M_OX * throttle + np.random.normal(0, 0.5, n_points)
    m_fuel = NOMINAL_M_FUEL * throttle + np.random.normal(0, 0.2, n_points)
    # Clamp: during engine-off phases, flow should be near zero
    data["m_ox"] = np.where(throttle < 0.01, np.maximum(0.0, np.random.normal(0, 0.3, n_points)), np.maximum(0.0, m_ox))
    data["m_fuel"] = np.where(throttle < 0.01, np.maximum(0.0, np.random.normal(0, 0.1, n_points)), np.maximum(0.0, m_fuel))
    
    # -------------------------------------------------------------------------
    # Physics relationship 1: Thrust = (m_ox + m_fuel) * Isp * g0 / 1000 [kN]
    # -------------------------------------------------------------------------
    thrust = (data["m_ox"] + data["m_fuel"]) * ISP * G0 / 1000.0
    data["F_thrust"] = np.maximum(0.0, thrust + np.random.normal(0, 2.0, n_points))
    
    # -------------------------------------------------------------------------
    # Physics relationship 2: Chamber Pressure P = k * (m_ox + m_fuel) [MPa]
    # This is a simplified empirical/physics-inspired relationship, NOT a
    # fundamental isentropic equation.
    # -------------------------------------------------------------------------
    data["P_chamber"] = np.maximum(0.0, K_CHAMBER * (data["m_ox"] + data["m_fuel"]) + np.random.normal(0, 0.05, n_points))
    
    # -------------------------------------------------------------------------
    # Chamber Temperature: ~3200K when firing (scaled by throttle), ~300K when off
    # Engine-off noise uses std=2K centered at 300K, min clamped to 285K
    # to avoid false anomalies from noise dipping below metadata min
    # -------------------------------------------------------------------------
    data["T_chamber"] = np.where(
        throttle > 0.05, 
        3200.0 * (0.8 + 0.2 * throttle) + np.random.normal(0, 15.0, n_points), 
        np.maximum(285.0, 300.0 + np.random.normal(0, 2.0, n_points))
    )
    
    # -------------------------------------------------------------------------
    # Turbopump Speed: N_pump ~ proportional to total flow rate
    # -------------------------------------------------------------------------
    data["N_pump"] = np.maximum(0.0, 104.0 * (data["m_ox"] + data["m_fuel"]) + np.random.normal(0, 150.0, n_points))
    
    # -------------------------------------------------------------------------
    # Tank pressures: decay as propellant empties
    # -------------------------------------------------------------------------
    data["P_tank_lox"] = np.maximum(0.5, 4.2 - 0.004 * np.minimum(t_series, 450) + np.random.normal(0, 0.02, n_points))
    data["P_tank_fuel"] = np.maximum(0.5, 3.5 - 0.003 * np.minimum(t_series, 450) + np.random.normal(0, 0.02, n_points))
    
    # -------------------------------------------------------------------------
    # Axial acceleration = Thrust / Mass (in g)
    # -------------------------------------------------------------------------
    data["acc_axial"] = np.maximum(0.0, (data["F_thrust"] * 1000.0) / (mass * G0) + np.random.normal(0, 0.03, n_points))
    
    # -------------------------------------------------------------------------
    # Vibrations: peak at Max-Q (60-90s) and Stage Separation (150s)
    # -------------------------------------------------------------------------
    vib_envelope = 0.5 + 4.5 * np.exp(-((t_series - 75)**2) / 200.0) + 6.0 * np.exp(-((t_series - 150)**2) / 25.0)
    data["vib_x"] = np.random.normal(0, vib_envelope, n_points)
    data["vib_y"] = np.random.normal(0, vib_envelope, n_points)
    data["vib_z"] = np.random.normal(0, vib_envelope * 1.2, n_points)
    
    # -------------------------------------------------------------------------
    # Electrical system
    # -------------------------------------------------------------------------
    data["v_batt"] = 28.0 - 0.002 * t_series + np.random.normal(0, 0.05, n_points)
    data["i_bus"] = 18.0 + 4.0 * throttle + np.random.normal(0, 0.3, n_points)
    
    # -------------------------------------------------------------------------
    # Thermal: Skin temperature from aerodynamic heating
    # -------------------------------------------------------------------------
    heating = 250.0 * np.exp(-((t_series - 100)**2) / 2500.0)
    data["T_skin"] = 300.0 + heating + np.random.normal(0, 1.0, n_points)
    
    # -------------------------------------------------------------------------
    # Attitude rates
    # -------------------------------------------------------------------------
    data["rate_roll"] = np.random.normal(0, 0.2, n_points)
    data["rate_pitch"] = np.random.normal(0, 0.1, n_points)
    data["rate_yaw"] = np.random.normal(0, 0.1, n_points)
    
    df = pd.DataFrame(data)
    
    if inject_anomalies:
        df = inject_synthetic_anomalies(df)
        
    return df


def inject_synthetic_anomalies(df: pd.DataFrame) -> pd.DataFrame:
    """Injects 5 types of anomalies as documented in INJECTED_ANOMALIES manifest.
    
    Injected faults:
        1. GAP: NaN values in P_chamber (T=120-123s) and m_ox (T=250-258s)
        2. DRIFT: Gradual +1.2 MPa bias in P_tank_lox (T=200-240s)
        3. NOISE: High-frequency noise in vib_x (T=300-330s)
        4. STUCK: v_batt frozen at 27.4V (T=180-210s)
        5. SPIKE: Transient +450K spike in T_skin (T≈380s)
    """
    # 1. GAP Injection (NaN values for missing data)
    # Short gap at T=120-123s (3 seconds) in P_chamber
    mask_gap_1 = (df["timestamp"] >= 120.0) & (df["timestamp"] <= 123.0)
    df.loc[mask_gap_1, "P_chamber"] = np.nan
    
    # Long gap at T=250-258s (8 seconds) in m_ox
    mask_gap_2 = (df["timestamp"] >= 250.0) & (df["timestamp"] <= 258.0)
    df.loc[mask_gap_2, "m_ox"] = np.nan
    
    # 2. DRIFT Injection (Sensor drift in P_tank_lox at T=200 to 240s)
    mask_drift = (df["timestamp"] >= 200.0) & (df["timestamp"] <= 240.0)
    drift_val = np.linspace(0, 1.2, mask_drift.sum())
    df.loc[mask_drift, "P_tank_lox"] += drift_val
    
    # 3. NOISE Injection (High frequency noise in vib_x at T=300 to 330s)
    mask_noise = (df["timestamp"] >= 300.0) & (df["timestamp"] <= 330.0)
    df.loc[mask_noise, "vib_x"] += np.random.normal(0, 8.0, mask_noise.sum())
    
    # 4. STUCK Sensor (v_batt stuck constant at T=180 to 210s)
    mask_stuck = (df["timestamp"] >= 180.0) & (df["timestamp"] <= 210.0)
    df.loc[mask_stuck, "v_batt"] = 27.4
    
    # 5. SPIKE Injection (Sudden transient spike in T_skin at T=380s)
    mask_spike = (df["timestamp"] >= 379.8) & (df["timestamp"] <= 380.2)
    df.loc[mask_spike, "T_skin"] += 450.0
    
    return df
