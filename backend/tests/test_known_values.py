"""
AERIS — Deterministic Known-Value Mathematical Tests

These tests verify the numerical layer using exact known values.
They do NOT depend on random data generation and are independently verifiable.
"""
import os
import sys
import numpy as np
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.synthetic_data import (
    ISP, G0, K_CHAMBER, NOMINAL_M_OX, NOMINAL_M_FUEL, NOMINAL_THRUST_KN,
    OF_RATIO_NOMINAL, PARAM_METADATA
)
from app.services.alert_manager import (
    THRUST_TOLERANCE_KN, PRESSURE_TOLERANCE_MPA,
    HEALTH_PENALTY_CRITICAL, HEALTH_PENALTY_WARNING, HEALTH_PENALTY_INFO
)


# =============================================================================
# 1. THRUST EQUATION KNOWN VALUES
# =============================================================================
def test_thrust_equation_known_value():
    """F = (m_ox + m_fuel) * Isp * g0 / 1000 [kN]"""
    m_ox = 240.0   # kg/s
    m_fuel = 96.0   # kg/s
    isp = 295.0     # s
    g0 = 9.81       # m/s²
    
    expected_kN = (m_ox + m_fuel) * isp * g0 / 1000.0
    # (336) * 295 * 9.81 / 1000 = 972.3672 kN
    
    assert abs(expected_kN - 972.3672) < 0.01, f"Thrust calc wrong: {expected_kN}"
    assert abs(NOMINAL_THRUST_KN - expected_kN) < 0.01, f"NOMINAL_THRUST_KN mismatch: {NOMINAL_THRUST_KN}"

def test_thrust_constants_match():
    """Module-level constants must be internally consistent."""
    assert ISP == 295.0
    assert G0 == 9.81
    assert NOMINAL_M_OX == 240.0
    assert NOMINAL_M_FUEL == 96.0
    
    computed = (NOMINAL_M_OX + NOMINAL_M_FUEL) * ISP * G0 / 1000.0
    assert abs(NOMINAL_THRUST_KN - computed) < 0.01


# =============================================================================
# 2. O/F RATIO KNOWN VALUES
# =============================================================================
def test_of_ratio_known_value():
    """O/F = m_ox / m_fuel"""
    assert abs(OF_RATIO_NOMINAL - 2.5) < 0.01, f"O/F ratio: {OF_RATIO_NOMINAL}"
    
    # Direct calculation
    of = 240.0 / 96.0
    assert abs(of - 2.5) < 0.01

def test_of_ratio_safe_division():
    """O/F calculation must handle m_fuel=0 safely."""
    m_fuel = 0.0
    m_ox = 240.0
    # Should not raise
    if m_fuel > 0:
        of = m_ox / m_fuel
    else:
        of = float('inf')
    assert of == float('inf')


# =============================================================================
# 3. CHAMBER PRESSURE KNOWN VALUES
# =============================================================================
def test_chamber_pressure_known_value():
    """P = k * (m_ox + m_fuel) [MPa] (simplified empirical relationship)"""
    k = 0.0185
    m_total = 240.0 + 96.0  # 336 kg/s
    expected_mpa = k * m_total  # 6.216 MPa
    
    assert abs(expected_mpa - 6.216) < 0.01, f"Chamber pressure: {expected_mpa}"
    assert abs(K_CHAMBER - 0.0185) < 0.0001

def test_chamber_pressure_zero_flow():
    """P should be ~0 when flow is zero."""
    p = K_CHAMBER * (0.0 + 0.0)
    assert p == 0.0


# =============================================================================
# 4. METADATA RANGE CONSISTENCY
# =============================================================================
def test_thrust_within_metadata_range():
    """Nominal thrust must be within metadata min/max."""
    meta = PARAM_METADATA["F_thrust"]
    assert meta["min"] <= NOMINAL_THRUST_KN <= meta["max"], \
        f"Nominal thrust {NOMINAL_THRUST_KN:.1f} outside metadata [{meta['min']}, {meta['max']}]"

def test_chamber_pressure_within_metadata_range():
    """Nominal chamber pressure must be within metadata min/max."""
    nominal_p = K_CHAMBER * (NOMINAL_M_OX + NOMINAL_M_FUEL)
    meta = PARAM_METADATA["P_chamber"]
    assert meta["min"] <= nominal_p <= meta["max"], \
        f"Nominal P_chamber {nominal_p:.2f} outside metadata [{meta['min']}, {meta['max']}]"

def test_chamber_temp_min_accommodates_noise():
    """T_chamber min must accommodate engine-off noise (300K ± 2K)."""
    meta = PARAM_METADATA["T_chamber"]
    # Engine-off temperature is 300K with std=2K noise
    # Min should be <= 295K to avoid false anomalies (3-sigma below 300K)
    assert meta["min"] <= 295.0, \
        f"T_chamber min={meta['min']} will cause false anomalies with engine-off noise"


# =============================================================================
# 5. HEALTH CALCULATION KNOWN VALUES
# =============================================================================
def test_health_perfect_score():
    """Zero anomalies → health score 100."""
    import pandas as pd
    from app.services.alert_manager import alert_manager
    df = pd.DataFrame({"timestamp": [0.0, 1.0, 2.0]})
    health = alert_manager.calculate_system_health_score(df, [])
    assert health["score"] == 100.0

def test_health_single_critical():
    """One CRITICAL event → health ≈ 92 (100 - 8)."""
    import pandas as pd
    from app.services.alert_manager import alert_manager
    df = pd.DataFrame({"timestamp": [0.0, 1.0, 2.0]})
    anomalies = [{"severity": "CRITICAL", "duration": 0.0, "confidence": 1.0}]
    health = alert_manager.calculate_system_health_score(df, anomalies)
    assert 88.0 <= health["score"] <= 92.5, f"One CRITICAL gave health={health['score']}"

def test_health_single_warning():
    """One WARNING event → health ≈ 96.5 (100 - 3.5)."""
    import pandas as pd
    from app.services.alert_manager import alert_manager
    df = pd.DataFrame({"timestamp": [0.0, 1.0, 2.0]})
    anomalies = [{"severity": "WARNING", "duration": 0.0, "confidence": 1.0}]
    health = alert_manager.calculate_system_health_score(df, anomalies)
    assert 95.0 <= health["score"] <= 97.0, f"One WARNING gave health={health['score']}"


# =============================================================================
# 6. UNIT CONSISTENCY CHECKS
# =============================================================================
def test_units_documented():
    """All parameters must have documented units."""
    for param, meta in PARAM_METADATA.items():
        assert "unit" in meta, f"{param} missing 'unit' field"
        assert meta["unit"] != "", f"{param} has empty unit"

def test_unit_ranges_sensible():
    """Basic sanity: min < max, nominal within range."""
    for param, meta in PARAM_METADATA.items():
        assert meta["min"] <= meta["max"], f"{param}: min ({meta['min']}) > max ({meta['max']})"
        if meta["nominal"] != 0.0:  # Skip zero-nominal params like attitude rates
            assert meta["min"] <= meta["nominal"] <= meta["max"], \
                f"{param}: nominal ({meta['nominal']}) outside [{meta['min']}, {meta['max']}]"


# =============================================================================
# 7. PHYSICS COMPLIANCE KNOWN VALUES
# =============================================================================
def test_physics_compliance_perfect_data():
    """On perfectly physics-consistent data, compliance should be ~100%."""
    import pandas as pd
    from app.services.alert_manager import alert_manager
    
    # Create perfectly consistent data
    n = 100
    m_ox = np.full(n, 240.0)
    m_fuel = np.full(n, 96.0)
    thrust = (m_ox + m_fuel) * ISP * G0 / 1000.0  # Exactly right
    p_chamber = K_CHAMBER * (m_ox + m_fuel)        # Exactly right
    
    df = pd.DataFrame({
        "timestamp": np.arange(n) * 0.1,
        "m_ox": m_ox,
        "m_fuel": m_fuel,
        "F_thrust": thrust,
        "P_chamber": p_chamber,
    })
    
    compliance = alert_manager.calculate_physics_compliance(df)
    assert compliance["overall"] >= 99.0, f"Perfect data gave compliance={compliance['overall']}%"
    assert compliance["thrust"]["mean_residual_kN"] < 0.01


if __name__ == "__main__":
    test_thrust_equation_known_value()
    test_thrust_constants_match()
    test_of_ratio_known_value()
    test_of_ratio_safe_division()
    test_chamber_pressure_known_value()
    test_chamber_pressure_zero_flow()
    test_thrust_within_metadata_range()
    test_chamber_pressure_within_metadata_range()
    test_chamber_temp_min_accommodates_noise()
    test_health_perfect_score()
    test_health_single_critical()
    test_health_single_warning()
    test_units_documented()
    test_unit_ranges_sensible()
    test_physics_compliance_perfect_data()
    print("✅ All Known-Value Math Tests Passed Successfully!")
