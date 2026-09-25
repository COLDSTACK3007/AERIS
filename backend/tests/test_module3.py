import os
import sys
import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.synthetic_data import generate_synthetic_telemetry
from app.services.anomaly_detector import anomaly_service
from app.services.physics_imputer import physics_imputer, ExtendedKalmanFilter
from app.ml.pinn_model import pinn_predictor

def test_pinn_predictor():
    timestamps = np.array([10.0, 20.0, 30.0])
    preds = pinn_predictor.predict_parameters(timestamps)
    assert "F_thrust" in preds
    assert "P_chamber" in preds
    assert len(preds["F_thrust"]) == 3
    assert np.all(preds["F_thrust"] >= 0.0)
    assert np.all(preds["P_chamber"] >= 0.0)

def test_pinn_status():
    """PINN must honestly report TRAINED or PROTOTYPE status."""
    assert pinn_predictor.status in ("TRAINED", "PROTOTYPE")

def test_extended_kalman_filter():
    ekf = ExtendedKalmanFilter(init_val=100.0, dt=0.1)
    pred_val = ekf.predict()
    assert isinstance(pred_val, float)
    updated_val = ekf.update(102.0)
    assert isinstance(updated_val, float)
    # After update, should be closer to measurement
    assert abs(updated_val - 102.0) < abs(pred_val - 102.0)

def test_ekf_with_initial_velocity():
    """EKF with non-zero initial velocity should predict trend."""
    ekf = ExtendedKalmanFilter(init_val=100.0, dt=0.1, init_velocity=10.0)
    pred = ekf.predict()
    # With velocity=10 and dt=0.1, predicted value should be ~101.0
    assert pred > 100.5, f"EKF prediction {pred} should trend upward with positive velocity"

def test_impute_telemetry_dataset():
    df = generate_synthetic_telemetry(duration=200.0, dt=0.5, inject_anomalies=True, random_seed=42)
    anomalies = anomaly_service.detect_all_anomalies(df)
    
    df_imp, imp_records = physics_imputer.impute_telemetry_dataset(df, anomalies)
    
    assert not df_imp.isna().any().any(), "Imputed DataFrame contains remaining NaNs!"
    assert len(imp_records) > 0
    
    # Check fields in imputation records
    methods = {r["method_used"] for r in imp_records}
    assert len(methods) > 0
    for r in imp_records:
        assert "timestamp" in r
        assert "parameter" in r
        assert "imputed_value" in r
        assert "confidence_score" in r
        assert 0.5 <= r["confidence_score"] <= 1.0, f"Confidence {r['confidence_score']} out of range"
        assert "physics_residual" in r
        assert "original_missing" in r
        assert r["original_missing"] == True
        assert "method_used" in r

def test_imputation_method_labels_honest():
    """Imputation method labels should NOT claim 'Isentropic' when using empirical relation."""
    df = generate_synthetic_telemetry(duration=200.0, dt=0.5, inject_anomalies=True, random_seed=42)
    anomalies = anomaly_service.detect_all_anomalies(df)
    
    _, imp_records = physics_imputer.impute_telemetry_dataset(df, anomalies)
    
    for r in imp_records:
        method = r["method_used"]
        # Should not falsely claim isentropic
        assert "Isentropic" not in method, f"Method falsely claims Isentropic: {method}"

def test_physical_bounds_pass():
    """Physical bounds pass should clamp negative values to zero."""
    df = pd.DataFrame({
        "timestamp": [0.0, 1.0],
        "P_chamber": [-1.0, 5.0],
        "F_thrust": [-10.0, 100.0],
        "m_ox": [0.0, 240.0],
        "m_fuel": [0.0, 96.0],
    })
    result = physics_imputer._apply_physical_bounds_pass(df)
    assert result["P_chamber"].iloc[0] == 0.0
    assert result["F_thrust"].iloc[0] == 0.0

if __name__ == "__main__":
    test_pinn_predictor()
    test_pinn_status()
    test_extended_kalman_filter()
    test_ekf_with_initial_velocity()
    test_impute_telemetry_dataset()
    test_imputation_method_labels_honest()
    test_physical_bounds_pass()
    print("✅ All Module 3 Unit Tests Passed Successfully!")
