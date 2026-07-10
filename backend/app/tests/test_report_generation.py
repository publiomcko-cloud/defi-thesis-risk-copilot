from fastapi.testclient import TestClient

from app.main import app
from app.rag.ingest import ingest_knowledge_base
from app.reports.markdown_export import render_markdown_report
from app.reports.templates import REQUIRED_REPORT_SECTIONS
from app.schemas.reports import ReportResponse


def test_generated_report_contains_required_sections() -> None:
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
        report_id = response.json()["report_id"]
        report_response = client.get(f"/api/reports/{report_id}")

    assert report_response.status_code == 200
    report = report_response.json()
    section_titles = {section["title"] for section in report["sections"]}

    assert set(REQUIRED_REPORT_SECTIONS).issubset(section_titles)
    assert report["executive_summary"]
    assert report["strategy_description"]
    assert report["sources"]
    assert report["missing_data"]
    assert report["disclaimer"]


def test_markdown_export_endpoint_returns_markdown() -> None:
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
        report_id = response.json()["report_id"]
        export_response = client.post(f"/api/reports/{report_id}/export")

    assert export_response.status_code == 200
    payload = export_response.json()
    assert payload["filename"] == f"{report_id}.md"
    assert "# Strategy Risk Report" in payload["markdown"]
    assert "## Risk Analysis" in payload["markdown"]
    assert "## Missing Data and Uncertainty" in payload["markdown"]
    assert "## Disclaimer" in payload["markdown"]


def test_markdown_renderer_validates_report_structure() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/analyze",
            json={
                "strategy_description": "Analyze an Aave lending market.",
                "protocols": ["aave"],
                "manual_inputs": {"liquidity_usd": 1_000_000},
                "analysis_depth": "standard",
            },
        )
        report = client.get(f"/api/reports/{response.json()['report_id']}").json()

    markdown = render_markdown_report(ReportResponse.model_validate(report))

    assert "## Executive Summary" in markdown
    assert "## Sources" in markdown
