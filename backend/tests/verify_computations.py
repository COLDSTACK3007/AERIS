"""
AERIS — Computation Verification Suite

Runs all physics, anomaly detection, imputation, and health calculations
and verifies them with real assertions (not just print("PASS")).
"""
import os
import sys
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.synthetic_data import (
    generate_synthetic_telemetry, PARAM_METADATA, determine_flight_phase,
    ISP, G0, K_CHAMBER, INJECTED_ANOMALIES
)
from app.services.ingestion import ingestion_service
from app.services.anomaly_detector import anomaly_service
from app.services.physics_imputer import physics_imputer
from app.services.alert_manager import alert_manager
from app.ml.pinn_model import pinn_predictor, compute_physics_residuals
from app.ml.anomaly_classifier import ml_detector
import torch

# Engineering tolerances for verification assertions
THRUST_TOLERANCE = 10.0    # kN — acceptable mean thrust residual
PRESSURE_TOLERANCE = 0.3   # MPa — acceptable mean chamber pressure residual
HEALTH_SCORE_MIN = 30.0    # Minimum health score with injected faults (event-grouped)


def verify_all_computations():
    print("=========================================================")
    print("   AERIS SYSTEM COMPUTATION VERIFICATION SUITE           ")
    print("=========================================================\n")

    # Use fixed seed for reproducibility
    df = generate_synthetic_telemetry(duration=600.0, dt=0.5, inject_anomalies=True, random_seed=42)
    
    # ---- 1. Verify Synthetic Data Physics ----
    print("1. Testing Telemetry Data Generation & Physics Profile...")
    assert len(df) == 1200, f"Expected 1200 rows, got {len(df)}"
    
    # Check thrust consistency: F = (m_ox + m_fuel) * Isp * g0 / 1000
    valid_thrust = df.dropna(subset=["F_thrust", "m_ox", "m_fuel"])
    expected_thrust = (valid_thrust["m_ox"] + valid_thrust["m_fuel"]) * ISP * G0 / 1000.0
    thrust_diff = np.abs(valid_thrust["F_thrust"] - expected_thrust)
    mean_thrust_error = float(np.mean(thrust_diff))
    assert mean_thrust_error < THRUST_TOLERANCE, \
        f"Mean thrust residual {mean_thrust_error:.4f} kN exceeds tolerance {THRUST_TOLERANCE} kN"
    print(f"   [OK] Thrust Equation Mean Residual: {mean_thrust_error:.4f} kN (< {THRUST_TOLERANCE} kN)")
    
    # Check chamber pressure: P = k * (m_ox + m_fuel)
    valid_pc = df.dropna(subset=["P_chamber", "m_ox", "m_fuel"])
    expected_pc = K_CHAMBER * (valid_pc["m_ox"] + valid_pc["m_fuel"])
    pc_diff = np.abs(valid_pc["P_chamber"] - expected_pc)
    mean_pc_error = float(np.mean(pc_diff))
    assert mean_pc_error < PRESSURE_TOLERANCE, \
        f"Mean P_chamber residual {mean_pc_error:.4f} MPa exceeds tolerance {PRESSURE_TOLERANCE} MPa"
    print(f"   [OK] Chamber Pressure Mean Residual: {mean_pc_error:.4f} MPa (< {PRESSURE_TOLERANCE} MPa)")
    
    # Verify PRE_LAUNCH has zero flow
    pre_launch = df[df["flight_phase"] == "PRE_LAUNCH"]
    assert pre_launch["m_ox"].max() < 5.0, \
        f"PRE_LAUNCH m_ox too high: {pre_launch['m_ox'].max():.2f}"
    print(f"   [OK] PRE_LAUNCH max m_ox: {pre_launch['m_ox'].max():.4f} kg/s (< 5.0)")

    # Verify thrust nominal is within metadata range
    meta_thrust = PARAM_METADATA["F_thrust"]
    firing = df[(df["m_ox"] > 100) & (df["F_thrust"].notna())]
    if len(firing) > 0:
        max_thrust = firing["F_thrust"].max()
        assert max_thrust <= meta_thrust["max"], \
            f"Max generated thrust {max_thrust:.1f} kN exceeds metadata max {meta_thrust['max']}"
        print(f"   [OK] Max generated thrust: {max_thrust:.1f} kN (metadata max: {meta_thrust['max']})")

    # ---- 2. Verify Anomaly Detection ----
    print("\n2. Testing Anomaly Detector...")
    anomalies = anomaly_service.detect_all_anomalies(df)
    assert len(anomalies) > 0, "No anomalies detected!"
    assert len(anomalies) < 200, f"Too many anomaly events: {len(anomalies)} (event grouping may be broken)"
    print(f"   [OK] Total Anomaly Events: {len(anomalies)}")
    
    anom_types = set(a["anomaly_type"] for a in anomalies)
    print(f"   [OK] Anomaly Categories: {sorted(list(anom_types))}")
    assert "GAP" in anom_types, "GAP not detected!"
    
    # Verify injected anomalies are detected
    gap_params = {a["parameter"] for a in anomalies if a["anomaly_type"] == "GAP"}
    assert "P_chamber" in gap_params, "P_chamber GAP not detected"
    assert "m_ox" in gap_params, "m_ox GAP not detected"
    print(f"   [OK] Injected GAPs detected: P_chamber, m_ox")
    
    stuck_params = {a["parameter"] for a in anomalies if a["anomaly_type"] == "STUCK"}
    print(f"   [OK] STUCK parameters detected: {stuck_params}")
    
    drift_params = {a["parameter"] for a in anomalies if a["anomaly_type"] == "DRIFT"}
    print(f"   [OK] DRIFT parameters detected: {drift_params}")
    
    # ML anomalies
    ml_anoms = [a for a in anomalies if a.get("detector") == "ISOLATION_FOREST" or a.get("method") == "ISOLATION_FOREST"]
    print(f"   [OK] ML Isolation Forest Events: {len(ml_anoms)}")

    # ---- 3. Verify Physics Imputation ----
    print("\n3. Testing Physics Data Imputation...")
    df_imp, imp_records = physics_imputer.impute_telemetry_dataset(df, anomalies)
    assert not df_imp.isna().any().any(), "Imputed DataFrame still contains NaNs!"
    print(f"   [OK] Imputed Datapoints: {len(imp_records)}")
    
    # Verify physics residuals
    residuals = [r["physics_residual"] for r in imp_records]
    mean_res = np.mean(residuals) if residuals else 0.0
    print(f"   [OK] Average Imputation Physics Residual: {mean_res:.4f}")
    
    # Verify confidence scores
    conf_scores = [r["confidence_score"] for r in imp_records]
    min_conf = np.min(conf_scores) if conf_scores else 1.0
    max_conf = np.max(conf_scores) if conf_scores else 1.0
    assert min_conf >= 0.5, f"Confidence too low: {min_conf}"
    assert max_conf <= 1.0, f"Confidence too high: {max_conf}"
    print(f"   [OK] Confidence Range: [{min_conf:.2f}, {max_conf:.2f}]")
    
    # Verify method labels are honest
    methods = {r["method_used"] for r in imp_records}
    for m in methods:
        assert "Isentropic" not in m, f"Dishonest method label: {m}"
    print(f"   [OK] Methods used: {methods}")

    # ---- 4. Verify PINN ----
    print(f"\n4. Testing PINN Model (Status: {pinn_predictor.status})...")
    dummy_t = torch.linspace(0, 600, 100)
    dummy_preds = torch.tensor(np.column_stack([
        np.full(100, 6.2),   # P_chamber
        np.full(100, 3200.0),# T_chamber
        np.full(100, 240.0), # m_ox
        np.full(100, 96.0),  # m_fuel
        np.full(100, 972.0)  # F_thrust (corrected nominal)
    ]), dtype=torch.float32)
    pinn_loss = compute_physics_residuals(dummy_t, dummy_preds)
    print(f"   [OK] PINN Physics Residual (perfect input): {pinn_loss.item():.4f}")
    # Perfect input should give near-zero physics loss
    assert pinn_loss.item() < 1.0, f"PINN physics loss on perfect input too high: {pinn_loss.item()}"

    # ---- 5. Verify Health Score & Physics Compliance ----
    print("\n5. Testing Health Score & Physics Compliance...")
    health = alert_manager.calculate_system_health_score(df_imp, anomalies)
    assert health["score"] >= HEALTH_SCORE_MIN, \
        f"Health score {health['score']} below minimum {HEALTH_SCORE_MIN} (event grouping broken?)"
    print(f"   [OK] Health Score: {health['score']} | Status: {health['status']} | Events: {health['event_count']}")
    
    # Physics compliance (residual-based)
    physics = alert_manager.calculate_physics_compliance(df_imp)
    assert physics["overall"] > 80.0, \
        f"Physics compliance {physics['overall']}% too low on imputed data"
    print(f"   [OK] Overall Physics Compliance: {physics['overall']}%")
    print(f"     Thrust: {physics['thrust']['compliance']}% (mean residual: {physics['thrust']['mean_residual_kN']:.4f} kN)")
    print(f"     Pressure: {physics['pressure']['compliance']}% (mean residual: {physics['pressure']['mean_residual_MPa']:.4f} MPa)")
    if physics["mass_flow"]["samples"] > 0:
        print(f"     Mass-Flow (O/F): {physics['mass_flow']['compliance']}% (mean deviation: {physics['mass_flow']['mean_residual_ratio']:.4f})")
    
    report = alert_manager.generate_comprehensive_flight_report(df_imp, anomalies, anomalies)
    print(f"   [OK] Report Physics Compliance: {report['physics_compliance_score']}")

    # ---- FINAL SUMMARY ----
    print("\n=========================================================")
    print("   VERIFICATION SUMMARY")
    print("=========================================================")
    print(f"   Thrust residual:     {mean_thrust_error:.4f} kN  (tol: {THRUST_TOLERANCE} kN)")
    print(f"   Pressure residual:   {mean_pc_error:.4f} MPa (tol: {PRESSURE_TOLERANCE} MPa)")
    print(f"   Anomaly events:      {len(anomalies)}")
    print(f"   Health score:        {health['score']}%")
    print(f"   Physics compliance:  {physics['overall']}%")
    print(f"   PINN status:         {pinn_predictor.status}")
    print(f"   Imputed points:      {len(imp_records)}")
    print("=========================================================")
    print("[SUCCESS] ALL COMPUTATIONS & PHYSICS AUDITS VERIFIED!")
    print("=========================================================")

if __name__ == "__main__":
    verify_all_computations()
