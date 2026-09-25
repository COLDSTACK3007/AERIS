import os
import sys
import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.synthetic_data import generate_synthetic_telemetry, PARAM_METADATA, determine_flight_phase

from app.services.ingestion import ingestion_service, RingBuffer

def test_synthetic_data_generation():
    df = generate_synthetic_telemetry(duration=60.0, dt=0.1, inject_anomalies=True, random_seed=42)
    assert not df.empty
    assert "timestamp" in df.columns
    assert "flight_phase" in df.columns
    assert len(df) == 600
    
    # Check 16 core telemetry parameters exist
    for param in PARAM_METADATA.keys():
        assert param in df.columns

def test_determine_flight_phase():
    # Fixed: 5.0s is PRE_LAUNCH (T <= 10s), not LIFTOFF
    assert determine_flight_phase(-5.0) == "PRE_LAUNCH"
    assert determine_flight_phase(0.0) == "PRE_LAUNCH"
    assert determine_flight_phase(5.0) == "PRE_LAUNCH"
    assert determine_flight_phase(10.0) == "PRE_LAUNCH"
    assert determine_flight_phase(10.1) == "LIFTOFF"
    assert determine_flight_phase(30.0) == "LIFTOFF"
    assert determine_flight_phase(75.0) == "MAX_Q"
    assert determine_flight_phase(120.0) == "STAGE_1_FLIGHT"
    assert determine_flight_phase(150.0) == "STAGE_1_FLIGHT"
    assert determine_flight_phase(155.0) == "STAGE_SEPARATION"
    assert determine_flight_phase(300.0) == "STAGE_2_FLIGHT"
    assert determine_flight_phase(500.0) == "COAST_ORBIT"

def test_pre_launch_zero_flow():
    """PRE_LAUNCH (T<=10s) must have near-zero flow rates and thrust."""
    df = generate_synthetic_telemetry(duration=600.0, dt=0.1, inject_anomalies=False, random_seed=42)
    pre_launch = df[df["flight_phase"] == "PRE_LAUNCH"]
    
    assert len(pre_launch) > 0
    # Flow rates should be near zero during pre-launch (only noise)
    assert pre_launch["m_ox"].max() < 5.0, f"m_ox during PRE_LAUNCH too high: {pre_launch['m_ox'].max():.2f}"
    assert pre_launch["m_fuel"].max() < 2.0, f"m_fuel during PRE_LAUNCH too high: {pre_launch['m_fuel'].max():.2f}"
    assert pre_launch["F_thrust"].max() < 15.0, f"F_thrust during PRE_LAUNCH too high: {pre_launch['F_thrust'].max():.2f}"

def test_thrust_metadata_consistency():
    """F_thrust nominal (~972 kN) must be within metadata max (1100 kN)."""
    from app.services.synthetic_data import NOMINAL_THRUST_KN
    meta = PARAM_METADATA["F_thrust"]
    assert NOMINAL_THRUST_KN < meta["max"], f"Nominal thrust {NOMINAL_THRUST_KN:.1f} exceeds metadata max {meta['max']}"
    assert abs(NOMINAL_THRUST_KN - 972.3) < 1.0, f"Expected ~972.3 kN, got {NOMINAL_THRUST_KN:.1f}"

def test_ring_buffer():
    rb = RingBuffer(capacity=10)
    for i in range(15):
        rb.append({"timestamp": i, "val": i * 2})
    assert len(rb.get_all()) == 10
    df_buf = rb.get_as_dataframe()
    assert len(df_buf) == 10
    assert df_buf.iloc[0]["timestamp"] == 5

def test_resample_multi_rate_data():
    # Construct raw data with multi-rate / duplicate timestamp points
    raw_data = {
        "timestamp": [0.0, 0.05, 0.1, 0.1, 0.2, 0.3],
        "F_thrust": [100.0, 105.0, 110.0, 112.0, 120.0, 130.0],
        "v_batt": [28.0, np.nan, 28.1, np.nan, 28.0, 27.9]
    }
    df_raw = pd.DataFrame(raw_data)
    df_resampled = ingestion_service.resample_multi_rate_data(df_raw, target_dt=0.1)
    
    assert "timestamp" in df_resampled.columns
    assert "flight_phase" in df_resampled.columns
    assert len(df_resampled) > 0
    assert not np.isnan(df_resampled.iloc[0]["F_thrust"])

def test_validate_record_ranges():
    record = {
        "timestamp": 10.0,
        "P_chamber": 15.0,  # Max is 8.0 (out of bounds with corrected metadata)
        "v_batt": 28.0      # Nominal
    }
    validated = ingestion_service.validate_record_ranges(record)
    assert "P_chamber" in validated["_out_of_bounds_params"]
    assert "v_batt" not in validated["_out_of_bounds_params"]

if __name__ == "__main__":
    test_synthetic_data_generation()
    test_determine_flight_phase()
    test_pre_launch_zero_flow()
    test_thrust_metadata_consistency()
    test_ring_buffer()
    test_resample_multi_rate_data()
    test_validate_record_ranges()
    print("✅ All Module 1 Unit Tests Passed Successfully!")
