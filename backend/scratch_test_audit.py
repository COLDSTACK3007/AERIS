import urllib.request
import json

BASE_URL = "http://127.0.0.1:8000/api"

def call_api(method, path, body=None):
    url = BASE_URL + path
    headers = {"Content-Type": "application/json"} if body else {}
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    with urllib.request.urlopen(req) as res:
        code = res.getcode()
        content = res.read().decode('utf-8')
        return code, json.loads(content)

print("Step 1: Generating synthetic telemetry (600s)...")
code, res1 = call_api("POST", "/synthetic/generate?duration=600.0&dt=0.1&inject_anomalies=true")
print(f"Synthetic generate: status={code}, msg={res1.get('message')}")

print("\nStep 2: Running anomaly detection...")
code, res2 = call_api("POST", "/anomaly/detect")
print(f"Anomaly detect: status={code}, total={res2.get('total_anomalies_detected')}")

print("\nStep 3: Running physics imputation...")
code, res3 = call_api("POST", "/imputation/run")
print(f"Imputation run: status={code}, total={res3.get('total_imputed_points')}")

print("\nStep 4: Fetching anomaly records...")
code, res4 = call_api("GET", "/anomaly/results")
print(f"Anomaly results count: {len(res4)}")

first_anomaly_id = res4[0]['id'] if res4 else 1

endpoints = [
    ("GET", "/telemetry/parameters", None),
    ("GET", "/telemetry/data?start_time=0&end_time=5", None),
    ("GET", "/anomaly/results", None),
    ("GET", "/imputation/results", None),
    ("GET", "/alerts/", None),
    ("GET", "/dashboard/summary", None),
    ("GET", "/dashboard/health", None),
    ("GET", "/dashboard/physics-compliance", None),
    ("GET", "/analysis/phase-baselines", None),
    ("GET", "/analysis/phase-anomalies", None),
    ("GET", "/analysis/scatter?x_param=m_ox&y_param=F_thrust", None),
    ("GET", "/analysis/drift", None),
    ("POST", "/analysis/whatif?parameter=m_ox&modification_pct=5.0", None),
    ("GET", "/analysis/evaluation-summary", None),
    ("GET", f"/analysis/anomaly/{first_anomaly_id}/deep-dive", None),
]

audit_report = []

for method, path, body in endpoints:
    try:
        c, data = call_api(method, path, body)
        payload_str = json.dumps(data)
        audit_report.append({
            "method": method,
            "path": path,
            "status": c,
            "payload_sample": payload_str[:120] + "..." if len(payload_str) > 120 else payload_str
        })
    except Exception as e:
        audit_report.append({
            "method": method,
            "path": path,
            "status": "ERROR: " + str(e),
            "payload_sample": ""
        })

print("\n=== FULL ENDPOINT AUDIT REPORT ===")
print(json.dumps(audit_report, indent=2))
