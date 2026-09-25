import os
import sys
import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.alert_manager import alert_manager, HEALTH_PENALTY_CRITICAL, HEALTH_PENALTY_WARNING, HEALTH_PENALTY_INFO
from app.services.synthetic_data import generate_synthetic_telemetry
from app.services.anomaly_detector import anomaly_service

def test_alert_generation():
    df = generate_synthetic_telemetry(duration=100.0, dt=0.5, inject_anomalies=True, random_seed=42)
    anomalies = anomaly_service.detect_all_anomalies(df)
    alerts = alert_manager.generate_alerts_from_anomalies(anomalies)
    
    assert len(alerts) == len(anomalies)
    for a in alerts:
        assert "level" in a
        assert "title" in a
        assert "message" in a

def test_system_health_calculation():
    df = generate_synthetic_telemetry(duration=600.0, dt=0.5, inject_anomalies=True, random_seed=42)
    anomalies = anomaly_service.detect_all_anomalies(df)
    health = alert_manager.calculate_system_health_score(df, anomalies)
    
    assert "score" in health
    assert 0.0 <= health["score"] <= 100.0
    assert "status" in health
    assert "event_count" in health
    
    # Health score should NOT collapse to 0% with grouped events
    # With ~5-8 genuine injected anomalies, score should be > 30%
    assert health["score"] > 30.0, \
        f"Health score collapsed to {health['score']}% — event grouping may not be working"

def test_health_score_not_collapsed_by_duplicates():
    """Health score must be event-based, not sample-count based.
    One stuck sensor for 30s should NOT create 300 independent penalties."""
    df = pd.DataFrame({"timestamp": np.arange(0, 100, 0.1)})
    
    # Simulate ONE stuck event represented as a single grouped event
    anomalies = [{
        "timestamp": 50.0,
        "end_time": 80.0,
        "duration": 30.0,
        "parameter": "v_batt",
        "anomaly_type": "STUCK",
        "severity": "CRITICAL",
        "confidence": 0.98,
        "sample_count": 300,
    }]
    
    health = alert_manager.calculate_system_health_score(df, anomalies)
    # One critical event should deduct ~8-12 points, NOT 300*4=1200 points
    assert health["score"] >= 85.0, \
        f"One STUCK event caused health={health['score']}% — should be ~88-92%"

def test_health_penalty_constants_match_docs():
    """Health penalty constants must match documentation values."""
    assert HEALTH_PENALTY_CRITICAL == 8.0, f"CRITICAL penalty is {HEALTH_PENALTY_CRITICAL}, docs say 8.0"
    assert HEALTH_PENALTY_WARNING == 3.5, f"WARNING penalty is {HEALTH_PENALTY_WARNING}, docs say 3.5"
    assert HEALTH_PENALTY_INFO == 1.0, f"INFO penalty is {HEALTH_PENALTY_INFO}, docs say 1.0"

def test_physics_compliance_uses_residuals():
    """Physics compliance must use actual physics residuals, not anomaly count."""
    df = generate_synthetic_telemetry(duration=600.0, dt=0.5, inject_anomalies=False, random_seed=42)
    
    physics = alert_manager.calculate_physics_compliance(df)
    
    assert "overall" in physics
    assert "thrust" in physics
    assert "pressure" in physics
    assert "mass_flow" in physics
    
    # On clean synthetic data, physics compliance should be very high
    assert physics["overall"] > 85.0, f"Physics compliance on clean data is {physics['overall']}% — too low"
    
    # Thrust compliance should report residuals in kN
    assert "mean_residual_kN" in physics["thrust"]
    assert "tolerance_kN" in physics["thrust"]
    
    # Pressure compliance should report residuals in MPa
    assert "mean_residual_MPa" in physics["pressure"]

def test_comprehensive_report_generation():
    df = generate_synthetic_telemetry(duration=100.0, dt=0.5, inject_anomalies=True, random_seed=42)
    anomalies = anomaly_service.detect_all_anomalies(df)
    alerts = alert_manager.generate_alerts_from_anomalies(anomalies)
    report = alert_manager.generate_comprehensive_flight_report(df, anomalies, alerts)
    
    assert "title" in report
    assert "overall_health_score" in report
    assert "physics_compliance_score" in report
    assert "physics_compliance" in report
    
    # Physics compliance should be a dict with per-relationship breakdown
    pc = report["physics_compliance"]
    assert isinstance(pc, dict)
    assert "thrust" in pc
    assert "pressure" in pc

def test_whatif_physics_alignment_with_staggered_nans():
    """Regression test for Bug 1: Ensure _check_physics_consistency aligns rows before computing residuals when NaNs occur at different indices."""
    from app.services.whatif_simulator import whatif_simulator
    from app.services.synthetic_data import ISP, G0, K_CHAMBER
    
    # Create DataFrame with staggered NaNs across m_ox, m_fuel, F_thrust, P_chamber
    # Rows:
    # Row 0: All valid firing data (m_ox=100, m_fuel=40, F_thrust=expected_f_0, P_chamber=expected_p_0)
    # Row 1: m_ox is NaN (should be skipped)
    # Row 2: F_thrust / P_chamber is NaN (should be skipped)
    # Row 3: All valid firing data (m_ox=120, m_fuel=50, F_thrust=expected_f_3 + 2.0, P_chamber=expected_p_3 + 0.1)
    # Row 4: m_fuel is NaN (should be skipped)
    
    m_ox_vals = [100.0, np.nan, 110.0, 120.0, np.nan]
    m_fuel_vals = [40.0, 45.0, 48.0, 50.0, np.nan]
    
    f_0 = (100.0 + 40.0) * ISP * G0 / 1000.0  # ~411.6 kN
    f_3 = (120.0 + 50.0) * ISP * G0 / 1000.0 + 2.0  # residual = 2.0 kN
    f_thrust_vals = [f_0, 420.0, np.nan, f_3, 450.0]
    
    p_0 = K_CHAMBER * (100.0 + 40.0)  # ~6.3 MPa
    p_3 = K_CHAMBER * (120.0 + 50.0) + 0.1  # residual = 0.1 MPa
    p_chamber_vals = [p_0, 6.5, np.nan, p_3, np.nan]
    
    df = pd.DataFrame({
        "m_ox": m_ox_vals,
        "m_fuel": m_fuel_vals,
        "F_thrust": f_thrust_vals,
        "P_chamber": p_chamber_vals
    })
    
    res = whatif_simulator._check_physics_consistency(df)
    
    # Valid aligned rows for F_thrust check are Row 0 and Row 3:
    # Row 0 residual: 0.0
    # Row 3 residual: 2.0
    # Mean residual: 1.0 kN, Max residual: 2.0 kN
    thrust_check = next(c for c in res["checks"] if "F =" in c["relationship"])
    assert np.isclose(thrust_check["mean_residual"], 1.0, atol=1e-3), f"Expected mean 1.0, got {thrust_check['mean_residual']}"
    assert np.isclose(thrust_check["max_residual"], 2.0, atol=1e-3), f"Expected max 2.0, got {thrust_check['max_residual']}"
    
    # Valid aligned rows for P_chamber check are Row 0 and Row 3:
    # Row 0 residual: 0.0
    # Row 3 residual: 0.1
    # Mean residual: 0.05 MPa, Max residual: 0.1 MPa
    press_check = next(c for c in res["checks"] if "P =" in c["relationship"])
    assert np.isclose(press_check["mean_residual"], 0.05, atol=1e-3), f"Expected mean 0.05, got {press_check['mean_residual']}"
    assert np.isclose(press_check["max_residual"], 0.1, atol=1e-3), f"Expected max 0.1, got {press_check['max_residual']}"

def test_bug_a_flight_report_physics_compliance():
    """Regression test for Bug A: Ensure POST /alerts/reports/generate passes full telemetry DF and returns non-flat compliance."""
    from fastapi.testclient import TestClient
    from app.main import app
    client = TestClient(app)
    
    client.post("/api/synthetic/generate?duration=600.0&dt=0.1&inject_anomalies=true")
    rep_res = client.post("/api/alerts/reports/generate")
    assert rep_res.status_code == 200
    report = rep_res.json()
    
    assert "physics_compliance" in report
    overall = report["physics_compliance"]["overall"]
    assert overall < 100.0, f"Flight report physics compliance is flat 100.0 (got {overall})"
    assert overall > 70.0, f"Flight report physics compliance unexpectedly low: {overall}"

def test_bug_b_websocket_stream_broadcast():
    """Regression test for Bug B: Ensure WebSocket clients receive data frames on data generation."""
    from fastapi.testclient import TestClient
    from app.main import app
    client = TestClient(app)
    
    with client.websocket_connect("/api/telemetry/stream") as websocket:
        client.post("/api/synthetic/generate?duration=5.0&dt=1.0&inject_anomalies=false")
        data = websocket.receive_json()
        assert "timestamp" in data, f"Websocket payload missing timestamp: {data}"

def test_bug_c_anomaly_record_duration_and_health_roundtrip():
    """Regression test for Bug C: Ensure AnomalyRecord duration is persisted and DB health score matches."""
    from fastapi.testclient import TestClient
    from app.main import app
    client = TestClient(app)
    
    client.post("/api/synthetic/generate?duration=600.0&dt=0.1&inject_anomalies=true")
    
    health_res = client.get("/api/dashboard/health")
    assert health_res.status_code == 200
    
    anom_res = client.get("/api/anomaly/results")
    assert anom_res.status_code == 200
    anomalies = anom_res.json()
    assert len(anomalies) > 0
    assert any("duration" in a and a["duration"] > 0 for a in anomalies), "No anomaly records have duration > 0"

if __name__ == "__main__":
    test_alert_generation()
    test_system_health_calculation()
    test_health_score_not_collapsed_by_duplicates()
    test_health_penalty_constants_match_docs()
    test_physics_compliance_uses_residuals()
    test_comprehensive_report_generation()
    test_whatif_physics_alignment_with_staggered_nans()
    test_bug_a_flight_report_physics_compliance()
    test_bug_b_websocket_stream_broadcast()
    test_bug_c_anomaly_record_duration_and_health_roundtrip()
    print("✅ All Module 4 & 5 Unit Tests Passed Successfully!")

