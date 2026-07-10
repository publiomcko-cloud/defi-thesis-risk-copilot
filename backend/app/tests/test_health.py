from fastapi.testclient import TestClient

from app.main import app


def test_health_returns_valid_json() -> None:
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "healthy"
    assert payload["service"] == "DeFi Thesis & Risk Copilot"
    assert "timestamp" in payload
