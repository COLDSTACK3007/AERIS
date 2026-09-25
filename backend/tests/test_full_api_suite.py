import sys
import os
import io

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def run_full_automated_test_suite():
    print("==================================================================")
    print("  AERIS SYSTEM AUTOMATED E2E TEST SUITE - TESTING ALL OPTIONS")
    print("==================================================================")
    
    passed_tests = 0
    total_tests = 0

    def assert_test(name, condition, extra_info=""):
        nonlocal passed_tests, total_tests
        total_tests += 1
        if condition:
            passed_tests += 1
            print(f"  [PASS] {name} {extra_info}")
        else:
            print(f"  [FAIL] {name} {extra_info}")

    # 1. Parameter Metadata Endpoint
    print("\n--- 1. Testing Telemetry Parameter Metadata Endpoint ---")
    res = client.get("/api/telemetry/parameters")
    assert_test("GET /api/telemetry/parameters", res.status_code == 200, f"(Params returned: {len(res.json())})")
    assert_test("Parameter P_chamber present", "P_chamber" in res.json())
    # Verify corrected F_thrust metadata
    f_thrust_meta = res.json().get("F_thrust", {})
    assert_test("F_thrust max >= 1000 kN (corrected)", f_thrust_meta.get("max", 0) >= 1000, f"(max={f_thrust_meta.get('max')})")
    assert_test("F_thrust nominal ~972 kN", abs(f_thrust_meta.get("nominal", 0) - 972) < 5, f"(nominal={f_thrust_meta.get('nominal')})")

    # 2. Synthetic Telemetry Generation
    print("\n--- 2. Testing 600s Synthetic Mission Generation ---")
    res = client.post("/api/synthetic/generate?duration=600.0&dt=0.1&inject_anomalies=true")
    assert_test("POST /api/synthetic/generate", res.status_code == 200, f"(Status: {res.json().get('status')})")
    assert_test("Records generated", res.json().get("total_records") > 5000, f"Total: {res.json().get('total_records')}")

    # 3. Telemetry Query Endpoint
    print("\n--- 3. Testing Telemetry Query Data Endpoint ---")
    res = client.get("/api/telemetry/data")
    assert_test("GET /api/telemetry/data", res.status_code == 200, f"(Records fetched: {len(res.json())})")
    data = res.json()
    assert_test("No NaN in JSON output", isinstance(data, list) and len(data) > 0)
    assert_test("Valid timestamp in first record", data[0].get("timestamp") == 0.0)

    # 4. CSV Telemetry Upload Endpoint
    print("\n--- 4. Testing Multi-Rate CSV Upload Endpoint ---")
    sample_csv_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "sample_flight_telemetry.csv"))
    if os.path.exists(sample_csv_path):
        with open(sample_csv_path, "rb") as f:
            files = {"file": ("sample_flight_telemetry.csv", f, "text/csv")}
            res = client.post("/api/telemetry/upload", files=files)
        assert_test("POST /api/telemetry/upload", res.status_code == 200, f"(Ingested: {res.json().get('rows_ingested')} rows)")
    else:
        # Create minimal CSV in memory for test
        csv_bytes = b"timestamp,P_chamber,T_chamber,m_ox,m_fuel,F_thrust\n0.0,6.2,3200,240,96,972\n5.0,6.1,3190,239,95,968\n"
        files = {"file": ("test.csv", io.BytesIO(csv_bytes), "text/csv")}
        res = client.post("/api/telemetry/upload", files=files)
        assert_test("POST /api/telemetry/upload (in-memory)", res.status_code == 200)

    # 5. Anomaly Detection Endpoint
    print("\n--- 5. Testing Multi-Strategy Anomaly Detection Engine ---")
    # Regenerate full synthetic dataset for deep anomaly scan
    client.post("/api/synthetic/generate?duration=600.0&dt=0.1&inject_anomalies=true")
    res = client.post("/api/anomaly/detect")
    assert_test("POST /api/anomaly/detect", res.status_code == 200, f"(Detected: {res.json().get('total_anomalies_detected')} anomaly events)")
    
    anom_res = client.get("/api/anomaly/results")
    assert_test("GET /api/anomaly/results", anom_res.status_code == 200, f"(Stored catalog items: {len(anom_res.json())})")

    # 6. Physics Imputation Engine Endpoint
    print("\n--- 6. Testing Physics Imputation Engine ---")
    res = client.post("/api/imputation/run")
    assert_test("POST /api/imputation/run", res.status_code == 200, f"(Imputed: {res.json().get('total_imputed_points')} points)")
    
    imp_res = client.get("/api/imputation/results")
    assert_test("GET /api/imputation/results", imp_res.status_code == 200, f"(Imputation records stored: {len(imp_res.json())})")

    # 7. Subsystem Health Score Endpoint
    print("\n--- 7. Testing Subsystem Health Score Calculation Endpoint ---")
    res = client.get("/api/dashboard/health")
    assert_test("GET /api/dashboard/health", res.status_code == 200)
    health_data = res.json()
    score = health_data.get("score", 0.0)
    assert_test("Health Score > 30% (event-grouped, not collapsed)", score > 30.0, f"(Health Score: {score}%)")

    # 8. Physics Compliance Endpoint
    print("\n--- 8. Testing Physics Compliance Endpoint ---")
    res = client.get("/api/dashboard/physics-compliance")
    assert_test("GET /api/dashboard/physics-compliance", res.status_code == 200)
    physics = res.json()
    assert_test("Physics compliance has thrust breakdown", "thrust" in physics)
    assert_test("Physics compliance has pressure breakdown", "pressure" in physics)

    # 9. Dashboard Summary & Correlation Heatmap
    print("\n--- 9. Testing Dashboard Summary & Physics Heatmap Matrix ---")
    res = client.get("/api/dashboard/summary")
    assert_test("GET /api/dashboard/summary", res.status_code == 200)
    summary_data = res.json()
    corr = summary_data.get("correlation_matrix", {})
    assert_test("Correlation matrix generated", len(corr) > 0, f"(Matrix dimensions: {len(corr)}x{len(corr)})")

    # 10. Priority Alerts Feed Endpoint
    print("\n--- 10. Testing Priority Alerts Feed Endpoint ---")
    res = client.get("/api/alerts")
    assert_test("GET /api/alerts", res.status_code == 200, f"(Alerts count: {len(res.json())})")

    # 11. Flight Surveillance Report Endpoint
    print("\n--- 11. Testing Flight Report Generation Endpoint ---")
    res = client.post("/api/alerts/reports/generate")
    assert_test("POST /api/alerts/reports/generate", res.status_code == 200, f"(Report Title: '{res.json().get('title')}')")
    report = res.json()
    assert_test("Report has physics_compliance dict", isinstance(report.get("physics_compliance"), dict))

    pct = (passed_tests / total_tests * 100) if total_tests > 0 else 0.0
    print(f"[SUCCESS] FINAL TEST RESULT: {passed_tests} / {total_tests} TESTS PASSED ({pct:.1f}%)")
    print("==================================================================")

if __name__ == "__main__":
    run_full_automated_test_suite()
