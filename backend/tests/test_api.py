"""FastAPI contract smoke tests."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_endpoint_reports_process_status():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_metadata_endpoint_returns_feature_schema():
    response = client.get("/api/v1/metadata")

    assert response.status_code == 200
    assert "feature_schema" in response.json()


def test_prediction_rejects_invalid_numeric_range():
    response = client.post("/api/v1/predictions", json={"annual_income": -1})

    assert response.status_code == 422
