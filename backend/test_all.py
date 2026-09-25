import sys
import os

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

def test_imports():
    print("Testing backend module imports...")
    from app.config import settings
    from app.database import engine, Base
    from app.models.telemetry import TelemetryRecord, ImputationRecord
    from app.models.anomaly import AnomalyRecord
    from app.models.alert import AlertRecord
    from app.services.synthetic_data import generate_synthetic_telemetry
    from app.services.ingestion import ingestion_service
    from app.services.anomaly_detector import anomaly_service
    from app.services.physics_imputer import physics_imputer
    from app.services.alert_manager import alert_manager
    from app.ml.pinn_model import TelemetryPINN
    from app.ml.anomaly_classifier import ml_detector
    
    print("All backend imports successful!")

def run_module1_tests():
    print("\n--- Running Module 1: Data Ingestion & Preprocessing Tests ---")
    from tests.test_module1 import (
        test_synthetic_data_generation,
        test_determine_flight_phase,
        test_pre_launch_zero_flow,
        test_thrust_metadata_consistency,
        test_ring_buffer,
        test_resample_multi_rate_data,
        test_validate_record_ranges
    )
    test_synthetic_data_generation()
    test_determine_flight_phase()
    test_pre_launch_zero_flow()
    test_thrust_metadata_consistency()
    test_ring_buffer()
    test_resample_multi_rate_data()
    test_validate_record_ranges()
    print("Module 1 Unit Tests PASSED!")

def run_module2_tests():
    print("\n--- Running Module 2: Anomaly Detection System Tests ---")
    from tests.test_module2 import (
        test_detect_all_anomalies_on_synthetic_data,
        test_injected_gap_detected,
        test_injected_stuck_detected,
        test_injected_drift_detected,
        test_injected_noise_detected,
        test_injected_spike_detected,
        test_no_false_positive_normal_thrust,
        test_no_false_drift_at_stage_transition,
        test_no_false_physics_violation_pre_launch,
        test_isolation_forest_ml_detector,
        test_physics_violation_detection
    )
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
    print("Module 2 Unit Tests PASSED!")

def run_module3_tests():
    print("\n--- Running Module 3: Physics-Constrained Data Imputation Tests ---")
    from tests.test_module3 import (
        test_pinn_predictor,
        test_pinn_status,
        test_extended_kalman_filter,
        test_ekf_with_initial_velocity,
        test_impute_telemetry_dataset,
        test_imputation_method_labels_honest,
        test_physical_bounds_pass
    )
    test_pinn_predictor()
    test_pinn_status()
    test_extended_kalman_filter()
    test_ekf_with_initial_velocity()
    test_impute_telemetry_dataset()
    test_imputation_method_labels_honest()
    test_physical_bounds_pass()
    print("Module 3 Unit Tests PASSED!")

def run_module4_5_tests():
    print("\n--- Running Module 4 & 5: Alert & Reporting System Tests ---")
    from tests.test_module4_5 import (
        test_alert_generation,
        test_system_health_calculation,
        test_health_score_not_collapsed_by_duplicates,
        test_health_penalty_constants_match_docs,
        test_physics_compliance_uses_residuals,
        test_comprehensive_report_generation
    )
    test_alert_generation()
    test_system_health_calculation()
    test_health_score_not_collapsed_by_duplicates()
    test_health_penalty_constants_match_docs()
    test_physics_compliance_uses_residuals()
    test_comprehensive_report_generation()
    print("Module 4 & 5 Unit Tests PASSED!")

def run_known_value_tests():
    print("\n--- Running Known-Value Mathematical Tests ---")
    from tests.test_known_values import (
        test_thrust_equation_known_value,
        test_thrust_constants_match,
        test_of_ratio_known_value,
        test_of_ratio_safe_division,
        test_chamber_pressure_known_value,
        test_chamber_pressure_zero_flow,
        test_thrust_within_metadata_range,
        test_chamber_pressure_within_metadata_range,
        test_chamber_temp_min_accommodates_noise,
        test_health_perfect_score,
        test_health_single_critical,
        test_health_single_warning,
        test_units_documented,
        test_unit_ranges_sensible,
        test_physics_compliance_perfect_data
    )
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
    print("Known-Value Math Tests PASSED!")

def run_computation_verification():
    from tests.verify_computations import verify_all_computations
    verify_all_computations()

def run_full_api_tests():
    from tests.test_full_api_suite import run_full_automated_test_suite
    run_full_automated_test_suite()

if __name__ == "__main__":
    test_imports()
    run_module1_tests()
    run_module2_tests()
    run_module3_tests()
    run_module4_5_tests()
    run_known_value_tests()
    run_computation_verification()
    run_full_api_tests()
    print("\n[SUCCESS] ALL BACKEND MODULE VERIFICATIONS & FULL API TEST SUITES PASSED SUCCESSFULLY!")
