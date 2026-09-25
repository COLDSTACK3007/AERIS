"""
Tests for the new Analysis Router and associated services:
  - Phase-relative anomaly detection
  - Parametric scatter analysis
  - Anomaly deep-dive
  - Predictive drift monitor
  - Mission what-if simulator
  - Evaluation summary
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import get_db, Base, engine, SessionLocal
from app.models.telemetry import TelemetryRecord, ImputationRecord
from app.models.anomaly import AnomalyRecord
from app.services.synthetic_data import generate_synthetic_telemetry

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    # Check if DB has telemetry data, if not seed it
    if db.query(TelemetryRecord).count() == 0:
        records, anomalies, imputations = generate_synthetic_telemetry()
        db.add_all(records)
        db.add_all(anomalies)
        db.add_all(imputations)
        db.commit()
    db.close()


def test_phase_baselines():
    response = client.get("/api/analysis/phase-baselines")
    assert response.status_code == 200
    data = response.json()
    assert "baselines" in data
    assert data["total_phases"] > 0


def test_phase_anomalies():
    response = client.get("/api/analysis/phase-anomalies")
    assert response.status_code == 200
    data = response.json()
    assert "anomalies" in data
    assert "total_phase_anomalies" in data


def test_scatter_data():
    response = client.get("/api/analysis/scatter?x_param=P_chamber&y_param=m_ox")
    assert response.status_code == 200
    data = response.json()
    assert data["x_param"] == "P_chamber"
    assert data["y_param"] == "m_ox"
    assert len(data["points"]) > 0


def test_scatter_data_invalid_param():
    response = client.get("/api/analysis/scatter?x_param=invalid_param&y_param=m_ox")
    assert response.status_code == 400


def test_drift_analysis():
    response = client.get("/api/analysis/drift")
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert data["total_parameters_analyzed"] > 0

    response_single = client.get("/api/analysis/drift?parameter=P_chamber")
    assert response_single.status_code == 200
    data_single = response_single.json()
    assert data_single["parameter"] == "P_chamber"


def test_whatif_simulation():
    response = client.post("/api/analysis/whatif?parameter=P_chamber&modification_pct=-10.0")
    assert response.status_code == 200
    data = response.json()
    assert data["modified_parameter"] == "P_chamber"
    assert "downstream_effects" in data
    assert "health_impact" in data


def test_evaluation_summary():
    response = client.get("/api/analysis/evaluation-summary")
    assert response.status_code == 200
    data = response.json()
    assert "mission" in data
    assert "anomaly_summary" in data
    assert "recovery_summary" in data
    assert "pinn_model" in data
    assert "health" in data


def test_deep_dive_endpoint():
    db = SessionLocal()
    anom = db.query(AnomalyRecord).first()
    db.close()
    if anom:
        response = client.get(f"/api/analysis/anomaly/{anom.id}/deep-dive")
        assert response.status_code == 200
        data = response.json()
        assert "basic_info" in data
        assert "observed_values" in data
        assert "attribution" in data
        assert "explanation" in data
