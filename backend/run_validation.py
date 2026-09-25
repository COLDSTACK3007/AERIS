import sys
import os

# Set up paths
backend_dir = r"d:\SIH PS2\backend"
sys.path.insert(0, backend_dir)
os.chdir(backend_dir)

print("=" * 60)
print("AERIS — Quick Validation Run")
print("=" * 60)

# 1. Known-value math tests
print("\n--- Known Value Tests ---")
from app.services.synthetic_data import (
    ISP, G0, K_CHAMBER, NOMINAL_M_OX, NOMINAL_M_FUEL, NOMINAL_THRUST_KN,
    OF_RATIO_NOMINAL, PARAM_METADATA
)

thrust_calc = (240.0 + 96.0) * 295.0 * 9.81 / 1000.0
assert abs(thrust_calc - 972.3672) < 0.1, f"Thrust calc: {thrust_calc}"
print(f"  ✓ Thrust equation: {thrust_calc:.4f} kN")

assert abs(NOMINAL_THRUST_KN - thrust_calc) < 0.01
print(f"  ✓ NOMINAL_THRUST_KN: {NOMINAL_THRUST_KN:.4f}")

assert PARAM_METADATA["F_thrust"]["max"] >= 1000
print(f"  ✓ F_thrust metadata max: {PARAM_METADATA['F_thrust']['max']}")

assert PARAM_METADATA["F_thrust"]["nominal"] == 972.0
print(f"  ✓ F_thrust metadata nominal: {PARAM_METADATA['F_thrust']['nominal']}")

assert PARAM_METADATA["T_chamber"]["min"] <= 295.0
print(f"  ✓ T_chamber min: {PARAM_METADATA['T_chamber']['min']}")

assert abs(OF_RATIO_NOMINAL - 2.5) < 0.01
print(f"  ✓ O/F ratio: {OF_RATIO_NOMINAL}")

p_nominal = K_CHAMBER * 336.0
assert abs(p_nominal - 6.216) < 0.01
print(f"  ✓ P_chamber nominal: {p_nominal:.4f} MPa")

# Verify all params have sensible ranges
for param, meta in PARAM_METADATA.items():
    assert meta["min"] <= meta["max"], f"{param}: min > max"
print(f"  ✓ All {len(PARAM_METADATA)} param ranges valid")

# 2. Synthetic data tests
print("\n--- Synthetic Data Tests ---")
from app.services.synthetic_data import generate_synthetic_telemetry, determine_flight_phase
import numpy as np

assert determine_flight_phase(5.0) == "PRE_LAUNCH"
print("  ✓ 5s → PRE_LAUNCH (fixed)")

df = generate_synthetic_telemetry(duration=600.0, dt=0.5, inject_anomalies=True, random_seed=42)
print(f"  ✓ Generated {len(df)} rows")

pre = df[df["flight_phase"] == "PRE_LAUNCH"]
assert pre["m_ox"].max() < 5.0, f"PRE_LAUNCH m_ox: {pre['m_ox'].max()}"
print(f"  ✓ PRE_LAUNCH max m_ox: {pre['m_ox'].max():.4f} (< 5.0)")

# Thrust consistency
valid = df.dropna(subset=["F_thrust", "m_ox", "m_fuel"])
expected = (valid["m_ox"] + valid["m_fuel"]) * ISP * G0 / 1000.0
residual = np.abs(valid["F_thrust"] - expected).mean()
assert residual < 10.0, f"Thrust residual: {residual}"
print(f"  ✓ Mean thrust residual: {residual:.4f} kN")

# Normal thrust within metadata
firing = df[(df["m_ox"] > 100) & df["F_thrust"].notna()]
if len(firing) > 0:
    assert firing["F_thrust"].max() <= 1100, f"Max thrust: {firing['F_thrust'].max()}"
    print(f"  ✓ Max thrust: {firing['F_thrust'].max():.1f} kN (< 1100)")

# 3. Anomaly Detection tests
print("\n--- Anomaly Detection Tests ---")
from app.services.anomaly_detector import anomaly_service

anomalies = anomaly_service.detect_all_anomalies(df)
print(f"  ✓ Detected {len(anomalies)} anomaly events")

types = {a["anomaly_type"] for a in anomalies}
print(f"  ✓ Types: {sorted(types)}")
assert "GAP" in types, "GAP not detected!"

gap_params = {a["parameter"] for a in anomalies if a["anomaly_type"] == "GAP"}
assert "P_chamber" in gap_params, "P_chamber GAP not detected"
assert "m_ox" in gap_params, "m_ox GAP not detected"
print(f"  ✓ GAP params: {gap_params}")

stuck_params = {a["parameter"] for a in anomalies if a["anomaly_type"] == "STUCK"}
print(f"  ✓ STUCK params: {stuck_params}")
if "v_batt" in stuck_params:
    print("  ✓ v_batt STUCK detected! (was missing before)")

drift_params = {a["parameter"] for a in anomalies if a["anomaly_type"] == "DRIFT"}
print(f"  ✓ DRIFT params: {drift_params}")
if "P_tank_lox" in drift_params:
    print("  ✓ P_tank_lox DRIFT detected! (was missing before)")

# No false positive on normal thrust
clean_df = generate_synthetic_telemetry(duration=600.0, dt=0.5, inject_anomalies=False, random_seed=42)
clean_anoms = anomaly_service.detect_all_anomalies(clean_df)
thrust_fps = [a for a in clean_anoms if a["parameter"] == "F_thrust" 
              and a["anomaly_type"] in ("SPIKE", "PHYSICS_VIOLATION")
              and a.get("flight_phase") in ("LIFTOFF", "MAX_Q", "STAGE_1_FLIGHT")]
assert len(thrust_fps) == 0, f"False positive thrust anomalies: {len(thrust_fps)}"
print(f"  ✓ No false positive thrust anomalies on clean data")

# 4. Physics Imputation
print("\n--- Physics Imputation Tests ---")
from app.services.physics_imputer import physics_imputer

df_imp, imp_records = physics_imputer.impute_telemetry_dataset(df, anomalies)
assert not df_imp.isna().any().any(), "NaNs remain after imputation!"
print(f"  ✓ Imputed {len(imp_records)} points, no NaNs remain")

for r in imp_records:
    assert "Isentropic" not in r["method_used"], f"Dishonest label: {r['method_used']}"
print(f"  ✓ Method labels honest (no false 'Isentropic' claims)")

# 5. Health Score
print("\n--- Health Score Tests ---")
from app.services.alert_manager import alert_manager

health = alert_manager.calculate_system_health_score(df_imp, anomalies)
assert health["score"] > 30.0, f"Health collapsed: {health['score']}"
print(f"  ✓ Health: {health['score']}% | Status: {health['status']} | Events: {health['event_count']}")

# Single event should NOT collapse score
import pandas as pd
single_df = pd.DataFrame({"timestamp": [0.0]})
single_anom = [{"severity": "CRITICAL", "duration": 30.0, "confidence": 0.98, "sample_count": 300}]
single_health = alert_manager.calculate_system_health_score(single_df, single_anom)
assert single_health["score"] >= 85.0, f"Single event collapsed to {single_health['score']}%"
print(f"  ✓ Single CRITICAL event: health={single_health['score']}% (not collapsed)")

# 6. Physics Compliance
print("\n--- Physics Compliance Tests ---")
physics = alert_manager.calculate_physics_compliance(df_imp)
print(f"  ✓ Overall: {physics['overall']}%")
print(f"    Thrust: {physics['thrust']['compliance']}% (residual: {physics['thrust']['mean_residual_kN']:.4f} kN)")
print(f"    Pressure: {physics['pressure']['compliance']}% (residual: {physics['pressure']['mean_residual_MPa']:.4f} MPa)")
assert physics["overall"] > 80.0, f"Physics compliance too low: {physics['overall']}%"

# Perfect data compliance
n = 100
perfect_df = pd.DataFrame({
    "timestamp": np.arange(n) * 0.1,
    "m_ox": np.full(n, 240.0),
    "m_fuel": np.full(n, 96.0),
    "F_thrust": np.full(n, 972.2616),
    "P_chamber": np.full(n, 6.216),
})
perfect_compliance = alert_manager.calculate_physics_compliance(perfect_df)
assert perfect_compliance["overall"] >= 99.0
print(f"  ✓ Perfect data compliance: {perfect_compliance['overall']}%")

# 7. PINN Status
print("\n--- PINN Status ---")
from app.ml.pinn_model import pinn_predictor
print(f"  ✓ PINN status: {pinn_predictor.status}")

print("\n" + "=" * 60)
print("🎉 ALL VALIDATION CHECKS PASSED!")
print("=" * 60)
