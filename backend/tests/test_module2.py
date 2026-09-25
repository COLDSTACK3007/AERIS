import os
import sys
import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.synthetic_data import generate_synthetic_telemetry, INJECTED_ANOMALIES
from app.services.anomaly_detector import anomaly_service
from app.ml.anomaly_classifier import ml_detector


def test_detect_all_anomalies_on_synthetic_data():
    """Basic: anomaly detector returns results with all required fields."""
    df = generate_synthetic_telemetry(duration=600.0, dt=0.5, inject_anomalies=True, random_seed=42)
    anomalies = anomaly_service.detect_all_anomalies(df)
    
    assert len(anomalies) > 0
    anomaly_types = {a["anomaly_type"] for a in anomalies}
    
    # Ensure primary categories are detected
    assert "GAP" in anomaly_types, f"GAP not detected. Types found: {anomaly_types}"
    
    # Ensure required fields are present in every anomaly event
    for a in anomalies:
        assert "timestamp" in a
        assert "parameter" in a
        assert "anomaly_type" in a
        assert "severity" in a
        assert "description" in a
        assert "confidence" in a


def test_injected_gap_detected():
    """GAP: Both P_chamber (120-123s) and m_ox (250-258s) gaps must be detected."""
    df = generate_synthetic_telemetry(duration=600.0, dt=0.5, inject_anomalies=True, random_seed=42)
    anomalies = anomaly_service.detect_all_anomalies(df)
    
    gap_anomalies = [a for a in anomalies if a["anomaly_type"] == "GAP"]
    gap_params = {a["parameter"] for a in gap_anomalies}
    
    assert "P_chamber" in gap_params, f"P_chamber GAP not detected. Gap params: {gap_params}"
    assert "m_ox" in gap_params, f"m_ox GAP not detected. Gap params: {gap_params}"
    
    # Verify timing for P_chamber gap
    pc_gap = [a for a in gap_anomalies if a["parameter"] == "P_chamber"]
    assert len(pc_gap) > 0
    assert abs(pc_gap[0]["timestamp"] - 120.0) < 2.0, f"P_chamber GAP start time wrong: {pc_gap[0]['timestamp']}"


def test_injected_stuck_detected():
    """STUCK: v_batt stuck at 27.4V during 180-210s must be detected."""
    df = generate_synthetic_telemetry(duration=600.0, dt=0.5, inject_anomalies=True, random_seed=42)
    anomalies = anomaly_service.detect_all_anomalies(df)
    
    stuck_anomalies = [a for a in anomalies if a["anomaly_type"] == "STUCK"]
    stuck_params = {a["parameter"] for a in stuck_anomalies}
    
    assert "v_batt" in stuck_params, f"v_batt STUCK not detected! Stuck params found: {stuck_params}"
    
    vbatt_stuck = [a for a in stuck_anomalies if a["parameter"] == "v_batt"]
    assert len(vbatt_stuck) > 0
    # Verify timing is approximately correct
    assert vbatt_stuck[0]["timestamp"] < 215.0, f"v_batt STUCK detected too late: T={vbatt_stuck[0]['timestamp']}"


def test_injected_drift_detected():
    """DRIFT: P_tank_lox drift during 200-240s must be detected."""
    df = generate_synthetic_telemetry(duration=600.0, dt=0.5, inject_anomalies=True, random_seed=42)
    anomalies = anomaly_service.detect_all_anomalies(df)
    
    drift_anomalies = [a for a in anomalies if a["anomaly_type"] == "DRIFT"]
    drift_params = {a["parameter"] for a in drift_anomalies}
    
    assert "P_tank_lox" in drift_params, f"P_tank_lox DRIFT not detected! Drift params found: {drift_params}"


def test_injected_noise_detected():
    """NOISE: vib_x high noise during 300-330s must be detected."""
    df = generate_synthetic_telemetry(duration=600.0, dt=0.5, inject_anomalies=True, random_seed=42)
    anomalies = anomaly_service.detect_all_anomalies(df)
    
    # Noise in vib_x may show up as NOISE type or as SPIKE/range violation
    # depending on severity. Check for any anomaly on vib_x in the right time range.
    vib_anomalies = [a for a in anomalies if a["parameter"] == "vib_x" 
                     and 295.0 <= a["timestamp"] <= 335.0]
    assert len(vib_anomalies) > 0, "No anomalies detected for vib_x in noise injection window (300-330s)"
    assert any(a["anomaly_type"] == "NOISE" for a in vib_anomalies), \
        f"vib_x anomaly type should be NOISE, got: {[a['anomaly_type'] for a in vib_anomalies]}"


def test_injected_spike_detected():
    """SPIKE: T_skin +450K spike at T≈380s must be detected."""
    df = generate_synthetic_telemetry(duration=600.0, dt=0.5, inject_anomalies=True, random_seed=42)
    anomalies = anomaly_service.detect_all_anomalies(df)
    
    spike_anomalies = [a for a in anomalies if a["anomaly_type"] == "SPIKE" 
                       and a["parameter"] == "T_skin"]
    assert len(spike_anomalies) > 0, "T_skin SPIKE not detected!"
    
    # Should be near T=380s
    spike_times = [a["timestamp"] for a in spike_anomalies]
    assert any(375.0 <= t <= 385.0 for t in spike_times), \
        f"T_skin SPIKE not at expected time ~380s. Times found: {spike_times}"


def test_no_false_positive_normal_thrust():
    """NEGATIVE: Normal Stage-1 thrust (~972 kN) should NOT trigger anomalies."""
    df = generate_synthetic_telemetry(duration=600.0, dt=0.5, inject_anomalies=False, random_seed=42)
    anomalies = anomaly_service.detect_all_anomalies(df)
    
    # No thrust-related SPIKE or PHYSICS_VIOLATION on F_thrust during nominal flight
    thrust_anomalies = [a for a in anomalies if a["parameter"] == "F_thrust" 
                        and a["anomaly_type"] in ("SPIKE", "PHYSICS_VIOLATION")
                        and a.get("flight_phase") in ("LIFTOFF", "MAX_Q", "STAGE_1_FLIGHT")]
    assert len(thrust_anomalies) == 0, \
        f"False positive on normal thrust! Anomalies: {thrust_anomalies}"


def test_no_false_drift_at_stage_transition():
    """NEGATIVE: Stage transitions should NOT be classified as DRIFT."""
    df = generate_synthetic_telemetry(duration=600.0, dt=0.5, inject_anomalies=False, random_seed=42)
    anomalies = anomaly_service.detect_all_anomalies(df)
    
    # No DRIFT anomalies at all on clean data
    drift_anomalies = [a for a in anomalies if a["anomaly_type"] == "DRIFT"]
    assert len(drift_anomalies) == 0, \
        f"False DRIFT detected on clean data: {[(a['parameter'], a['timestamp']) for a in drift_anomalies]}"


def test_no_false_physics_violation_pre_launch():
    """NEGATIVE: PRE_LAUNCH zero flow should NOT trigger physics violations."""
    df = generate_synthetic_telemetry(duration=600.0, dt=0.5, inject_anomalies=False, random_seed=42)
    anomalies = anomaly_service.detect_all_anomalies(df)
    
    pre_launch_violations = [a for a in anomalies 
                             if a.get("flight_phase") == "PRE_LAUNCH" 
                             and a["anomaly_type"] == "PHYSICS_VIOLATION"]
    assert len(pre_launch_violations) == 0, \
        f"False physics violation during PRE_LAUNCH: {pre_launch_violations}"


def test_isolation_forest_ml_detector():
    df = generate_synthetic_telemetry(duration=100.0, dt=0.5, inject_anomalies=True, random_seed=42)
    ml_anoms = ml_detector.detect_multivariate_ml_anomalies(df, ["F_thrust", "P_chamber", "m_ox"])
    assert isinstance(ml_anoms, list)


def test_physics_violation_detection():
    # Construct synthetic physics violation (mass flow without thrust)
    t = np.arange(0, 100, 0.5)
    df = pd.DataFrame({
        "timestamp": t,
        "flight_phase": ["STAGE_1_FLIGHT"] * len(t),
        "m_ox": [240.0] * len(t),
        "m_fuel": [96.0] * len(t),
        "F_thrust": [0.0] * len(t)  # Violation!
    })
    anomalies = anomaly_service._detect_correlation_breakdowns(df)
    assert len(anomalies) > 0
    assert any(a["anomaly_type"] == "PHYSICS_VIOLATION" for a in anomalies)


if __name__ == "__main__":
    test_detect_all_anomalies_on_synthetic_data()
    test_injected_gap_detected()
    test_injected_stuck_detected()
    test_injected_drift_detected()
    test_injected_noise_detected()
    test_injected_spike_detected()
    test_no_false_positive_normal_thrust()
    test_no_false_drift_at_stage_transition()
    test_no_false_physics_violation_pre_launch()
    test_isolation_forest_ml_detector()
    test_physics_violation_detection()
    print("✅ All Module 2 Unit Tests Passed Successfully!")
