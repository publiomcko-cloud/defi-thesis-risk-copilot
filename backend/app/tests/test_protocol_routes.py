from fastapi.testclient import TestClient

from app.main import app


def test_protocols_returns_initial_mvp_protocols() -> None:
    client = TestClient(app)

    response = client.get("/api/protocols")

    assert response.status_code == 200
    payload = response.json()
    protocol_ids = {protocol["id"] for protocol in payload["protocols"]}
    assert {"pendle", "morpho", "aave"}.issubset(protocol_ids)
