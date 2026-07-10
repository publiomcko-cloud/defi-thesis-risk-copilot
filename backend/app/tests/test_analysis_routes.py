from fastapi.testclient import TestClient

from app.main import app


def test_analyze_returns_report_id_and_report_can_be_retrieved() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/analyze",
        json={
            "strategy_description": "Analyze a Pendle PT strategy using Morpho borrow.",
            "protocols": ["pendle", "morpho"],
            "manual_inputs": {},
            "analysis_depth": "standard",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["report_id"].startswith("report_")
    assert payload["risk_rating"] == "Aggressive"

    report_response = client.get(f"/api/reports/{payload['report_id']}")
    assert report_response.status_code == 200
    report = report_response.json()
    assert report["report_id"] == payload["report_id"]
    assert report["protocols"] == ["morpho", "pendle"]
    assert report["missing_data"]
    assert "financial advice" in report["disclaimer"]


def test_document_ingest_returns_queued_mock_response() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/documents/ingest",
        json={"protocol": "pendle", "title": "Pendle demo doc"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "queued"
    assert payload["document_id"].startswith("doc_pendle_")


def test_market_data_fetch_returns_missing_fields() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/market-data/fetch",
        json={
            "protocols": ["pendle", "morpho"],
            "manual_inputs": {"borrow_apy": 0.07},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "mocked"
    assert "live_liquidity" in payload["missing_fields"]
    assert payload["data"]["manual_inputs"]["borrow_apy"] == 0.07
