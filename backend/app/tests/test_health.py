from fastapi.testclient import TestClient

from app.main import app


def test_root_describes_service_without_secrets() -> None:
    with TestClient(app) as client:
        response = client.get("/")

    assert response.status_code == 200
    payload = response.json()
    assert payload["service"] == "DeFi Thesis & Risk Copilot"
    assert payload["status"] == "online"
    assert payload["health"] == "/health"
    assert payload["readiness"] == "/ready"
    assert "secret" not in str(payload).lower()


def test_health_returns_valid_json_and_request_id() -> None:
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "healthy"
    assert payload["service"] == "DeFi Thesis & Risk Copilot"
    assert "timestamp" in payload
    assert response.headers["x-request-id"]


def test_readiness_checks_database_in_local_mode() -> None:
    with TestClient(app) as client:
        response = client.get("/ready")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ready"
    assert payload["database"] is True
    assert "rag_index" in payload
