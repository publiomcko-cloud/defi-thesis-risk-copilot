from pathlib import Path

from fastapi.testclient import TestClient

from app.agents.orchestrator import run_analysis_workflow
from app.db.session import SessionLocal
from app.main import app
from app.rag.ingest import ingest_knowledge_base
from app.rag.vector_store import DEFAULT_INDEX_PATH
from app.schemas.analysis import AnalysisRequest


def test_orchestrator_runs_complete_controlled_workflow() -> None:
    ingest_knowledge_base()
    request = AnalysisRequest(
        strategy_description=(
            "Analyze a hypothetical Pendle PT strategy using Morpho borrow. "
            "Evaluate oracle risk, liquidation risk, and exit before maturity."
        ),
        protocols=["pendle", "morpho"],
        manual_inputs={},
        analysis_depth="standard",
    )

    with SessionLocal() as db:
        result = run_analysis_workflow(request, "report_workflow_test", db)

    assert result.parsed_strategy.protocols == ["morpho", "pendle"]
    assert result.retrieved_context
    assert result.market_data.data["adapters"]
    assert result.risk_score.rating in {
        "Conservative",
        "Moderate",
        "Aggressive",
        "Very Risky",
    }
    assert result.report.report_id == "report_workflow_test"
    assert result.report.sources
    assert any(section.title == "Market Data Summary" for section in result.report.sections)
    assert any(section.title == "Risk Analysis" for section in result.report.sections)
    assert "financial advice" in result.report.disclaimer


def test_api_analyze_persists_complete_workflow_report() -> None:
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
        report_response = client.get(f"/api/reports/{payload['report_id']}")

    assert report_response.status_code == 200
    report = report_response.json()
    assert report["risk_rating"] == payload["risk_rating"]
    assert report["sources"]
    assert any(section["title"] == "Stress Scenarios" for section in report["sections"])
    assert report["disclaimer"]


def test_workflow_returns_partial_report_when_rag_index_is_missing() -> None:
    original_path = Path(DEFAULT_INDEX_PATH)
    backup_path = original_path.with_suffix(".json.bak")
    if original_path.exists():
        original_path.replace(backup_path)

    try:
        request = AnalysisRequest(
            strategy_description="Analyze an unknown DeFi strategy.",
            protocols=["pendle"],
            manual_inputs={},
            analysis_depth="standard",
        )
        with SessionLocal() as db:
            result = run_analysis_workflow(request, "report_no_rag_test", db)

        assert not result.retrieved_context
        assert "Retrieved protocol documentation" in result.missing_data
        assert any(
            section.title == "Sources"
            and "No local RAG sources were retrieved" in section.content
            for section in result.report.sections
        )
        assert result.report.disclaimer
    finally:
        if backup_path.exists():
            backup_path.replace(original_path)
