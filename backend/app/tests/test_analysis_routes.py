from fastapi.testclient import TestClient

from app.db.session import SessionLocal
from app.main import app
from app.models.analysis_request import AnalysisRequestModel
from app.models.report import ReportModel
from app.rag.ingest import ingest_knowledge_base


def test_analyze_returns_report_id_and_report_can_be_retrieved() -> None:
    ingest_knowledge_base()

    with TestClient(app) as client:
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
        assert "Retrieved protocol documentation" not in report["missing_data"]
        assert "financial advice" in report["disclaimer"]
        assert any(source["source_type"] == "knowledge_base" for source in report["sources"])
        assert any(section["title"] == "Market data summary" for section in report["sections"])

    with SessionLocal() as db:
        report_record = db.get(ReportModel, payload["report_id"])
        assert report_record is not None
        analysis_record = db.get(AnalysisRequestModel, report_record.analysis_request_id)
        assert analysis_record is not None
        assert analysis_record.protocols == ["morpho", "pendle"]


def test_document_ingest_returns_queued_mock_response() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/documents/ingest",
            json={"protocol": "pendle", "title": "Pendle demo doc"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "queued"
    assert payload["document_id"] == "local_rag_pendle"
    assert "refreshed the local curated RAG index" in payload["message"]


def test_market_data_fetch_returns_missing_fields() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/market-data/fetch",
            json={
                "protocols": ["pendle", "morpho"],
                "manual_inputs": {"borrow_apy": 0.07},
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "partial"
    assert "manual.implied_apy" in payload["missing_fields"]
    manual_adapter = next(
        item for item in payload["data"]["adapters"] if item["source"] == "manual"
    )
    assert manual_adapter["data"]["borrow_apy"] == 0.07
