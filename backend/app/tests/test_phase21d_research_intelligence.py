from __future__ import annotations

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.service import create_user
from app.core.config import get_settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.analysis_request import AnalysisRequestModel
from app.models.knowledge import (
    KnowledgeChunkModel,
    KnowledgeDocumentModel,
    KnowledgeDocumentVersionModel,
    KnowledgeSourceModel,
)
from app.models.report import ReportModel
from app.models.research_intelligence import ThesisAssumptionModel, ThesisRevisionModel
from app.models.saved_thesis import SavedThesisModel
from app.models.organization import OrganizationMembershipModel, OrganizationModel
from app.schemas.reports import CitationLineageReference, ReportResponse, ReportSection, SourceReference


@pytest.fixture(autouse=True)
def clear_settings_cache() -> None:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def research_client(monkeypatch):
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("AUTH_PROVIDER", "legacy_local")
    monkeypatch.setenv("AUTH_SECRET_KEY", "phase21d-research-secret")
    monkeypatch.setenv("APP_ENV", "development")
    get_settings.cache_clear()
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    with Session() as db:
        owner = create_user(db, "phase21d-owner@example.test", token="phase21d-owner-token")
        other = create_user(db, "phase21d-other@example.test", token="phase21d-other-token")
        identities = {"owner": owner.id, "other": other.id}
        organization = OrganizationModel(
            id="org_phase21d",
            name="Phase 21D organization",
            slug="phase-21d-organization",
            status="active",
            created_by_user_id=owner.id,
        )
        db.add_all([
            organization,
            OrganizationMembershipModel(
                id="membership_phase21d_owner",
                organization_id=organization.id,
                user_id=owner.id,
                role="owner",
                status="active",
            ),
            OrganizationMembershipModel(
                id="membership_phase21d_other",
                organization_id=organization.id,
                user_id=other.id,
                role="member",
                status="active",
            ),
        ])
        _persist_report(db, "report_phase21d_left", owner.id, "Left strategy", "Moderate")
        _persist_report(db, "report_phase21d_right", owner.id, "Right strategy", "Aggressive")
        _persist_report(db, "report_phase21d_other", other.id, "Other strategy", "Conservative")
        _persist_lineaged_report(db, owner.id)
        db.commit()

    def override_get_db():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app), Session, identities
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()


def test_thesis_history_assumptions_catalysts_and_monitoring_are_append_only(research_client) -> None:
    client, Session, _ = research_client
    headers = {"Authorization": "Bearer phase21d-owner-token"}
    created = client.post(
        "/api/theses",
        headers=headers,
        json={
            "title": "Pendle maturity thesis",
            "strategy_text": "Research the maturity and liquidity risks of the Pendle position.",
            "protocols": ["pendle"],
            "assumptions": {"legacy": "kept exactly"},
            "visibility": "private",
        },
    )
    assert created.status_code == 200
    thesis_id = created.json()["id"]

    history = client.get(f"/api/theses/{thesis_id}/history", headers=headers)
    assert history.status_code == 200
    assert [item["revision_number"] for item in history.json()["items"]] == [1]
    assert history.json()["items"][0]["assumptions_snapshot"] == {"legacy": "kept exactly"}

    assumption = client.post(
        f"/api/theses/{thesis_id}/assumptions",
        headers=headers,
        json={"statement": "Buy only after a maturity review.", "evidence_references": [{"unverified_reference": "User research note"}]},
    )
    assert assumption.status_code == 200
    assumption_id = assumption.json()["id"]
    revised = client.patch(
        f"/api/theses/{thesis_id}/assumptions/{assumption_id}",
        headers=headers,
        json={
            "statement": "Maturity evidence is weaker than previously recorded.",
            "state": "weakened",
            "expected_revision": 1,
            "evidence_references": [{"unverified_reference": "Follow-up review"}],
        },
    )
    assert revised.status_code == 200
    assert revised.json()["revision_number"] == 2
    assumptions = client.get(f"/api/theses/{thesis_id}/assumptions", headers=headers).json()["items"]
    assert [(item["revision_number"], item["state"]) for item in assumptions] == [(1, "active"), (2, "weakened")]

    catalyst = client.post(
        f"/api/theses/{thesis_id}/catalysts",
        headers=headers,
        json={
            "title": "Market maturity",
            "date_precision": "window",
            "window_start": "2027-01-01",
            "window_end": "2027-01-31",
            "uncertainty": "The source only supports a month-long window.",
            "evidence_references": [{"unverified_reference": "Calendar note"}],
        },
    )
    assert catalyst.status_code == 200
    assert catalyst.json()["date_precision"] == "window"
    assert client.post(
        f"/api/theses/{thesis_id}/catalysts",
        headers=headers,
        json={"title": "Unsafe date", "date_precision": "exact"},
    ).status_code == 422

    questions = client.get(f"/api/theses/{thesis_id}/monitoring-questions", headers=headers)
    assert questions.status_code == 200
    assert questions.json()["origin_type"] == "deterministic"
    assert all("buy" not in item.lower() for item in questions.json()["questions"])
    assert all("schedule" not in item.lower() for item in questions.json()["questions"])

    with Session() as db:
        assert len(db.scalars(select(ThesisRevisionModel).where(ThesisRevisionModel.thesis_id == thesis_id)).all()) >= 4
        assert len(db.scalars(select(ThesisAssumptionModel).where(ThesisAssumptionModel.thesis_id == thesis_id)).all()) == 2
    exported = client.get("/api/account/export", headers=headers)
    assert exported.status_code == 200
    assert exported.json()["thesis_revisions"]
    assert exported.json()["research_assumptions"]


def test_legacy_thesis_baseline_and_deletion_do_not_leave_research_access(research_client) -> None:
    client, Session, identities = research_client
    headers = {"Authorization": "Bearer phase21d-owner-token"}
    with Session() as db:
        legacy = SavedThesisModel(
            id="thesis_phase21d_legacy",
            owner_user_id=identities["owner"],
            title="Legacy thesis",
            strategy_text="Legacy thesis text remains exactly as stored.",
            protocols=["pendle"],
            assumptions_json={"old": "untouched"},
            visibility="private",
        )
        db.add(legacy)
        db.commit()
    history = client.get("/api/theses/thesis_phase21d_legacy/history", headers=headers)
    assert history.status_code == 200
    assert history.json()["items"][0]["origin"] == "legacy_baseline"
    assert history.json()["items"][0]["assumptions_snapshot"] == {"old": "untouched"}
    assert client.delete("/api/theses/thesis_phase21d_legacy", headers=headers).status_code == 200
    assert client.get("/api/theses/thesis_phase21d_legacy/history", headers=headers).status_code == 404
    with Session() as db:
        assert not db.scalars(select(ThesisRevisionModel).where(ThesisRevisionModel.thesis_id == "thesis_phase21d_legacy")).all()


def test_report_comparison_scope_staleness_and_scenario_outputs_are_deterministic(research_client) -> None:
    client, Session, _ = research_client
    headers = {"Authorization": "Bearer phase21d-owner-token"}
    comparison = client.post(
        "/api/reports/compare",
        headers=headers,
        json={"left_report_id": "report_phase21d_left", "right_report_id": "report_phase21d_right"},
    )
    assert comparison.status_code == 200
    assert comparison.json()["origin_type"] == "deterministic"
    assert comparison.json()["changes"]["risk_rating"]["status"] == "changed"
    repeated = client.post(
        "/api/reports/compare",
        headers=headers,
        json={"left_report_id": "report_phase21d_left", "right_report_id": "report_phase21d_right"},
    )
    assert repeated.json()["id"] == comparison.json()["id"]
    denied = client.post(
        "/api/reports/compare",
        headers=headers,
        json={"left_report_id": "report_phase21d_left", "right_report_id": "report_phase21d_other"},
    )
    assert denied.status_code == 404

    current = client.get("/api/reports/report_phase21d_lineage/source-staleness", headers=headers)
    assert current.status_code == 200
    assert current.json()["items"][0]["status"] == "current"
    with Session() as db:
        document = db.get(KnowledgeDocumentModel, "document_phase21d")
        db.add(
            KnowledgeDocumentVersionModel(
                id="version_phase21d_new",
                document_id=document.id,
                version_number=2,
                storage_key="phase21d/new",
                checksum="b" * 64,
                size_bytes=2,
                status="ready",
            )
        )
        document.current_version_id = "version_phase21d_new"
        db.commit()
    assert client.get("/api/reports/report_phase21d_lineage/source-staleness", headers=headers).json()["items"][0]["status"] == "superseded"

    scenario = client.post(
        "/api/research/scenarios/compare",
        headers=headers,
        json={
            "left": {"strategy_description": "Left", "borrow_apy": 0.05, "supply_apy": 0.1},
            "right": {"strategy_description": "Right", "borrow_apy": 0.08, "supply_apy": 0.1},
        },
    )
    assert scenario.status_code == 200
    assert scenario.json()["origin_type"] == "deterministic"
    assert "not forecasts" in scenario.json()["disclaimer"].lower()


def test_organization_membership_revocation_and_deletion_remove_research_access(research_client) -> None:
    client, Session, _ = research_client
    owner_headers = {"Authorization": "Bearer phase21d-owner-token"}
    member_headers = {"Authorization": "Bearer phase21d-other-token"}
    created = client.post(
        "/api/theses",
        headers=owner_headers,
        json={
            "title": "Organization thesis",
            "strategy_text": "Organization-only research remains visible to active members.",
            "protocols": ["pendle"],
            "assumptions": {},
            "organization_id": "org_phase21d",
            "visibility": "organization",
        },
    )
    assert created.status_code == 200
    thesis_id = created.json()["id"]
    assert client.get(f"/api/theses/{thesis_id}/history", headers=member_headers).status_code == 200
    with Session() as db:
        membership = db.get(OrganizationMembershipModel, "membership_phase21d_other")
        membership.status = "removed"
        db.commit()
    assert client.get(f"/api/theses/{thesis_id}/history", headers=member_headers).status_code == 404
    assert client.delete("/api/organizations/org_phase21d", headers=owner_headers).status_code == 200
    assert client.get(f"/api/theses/{thesis_id}/history", headers=owner_headers).status_code == 404
    with Session() as db:
        assert not db.scalars(select(ThesisRevisionModel).where(ThesisRevisionModel.thesis_id == thesis_id)).all()


def _persist_report(db, report_id: str, owner_user_id: str, strategy: str, risk_rating: str) -> None:
    analysis = AnalysisRequestModel(
        id=f"analysis_{report_id}",
        strategy_description=strategy,
        protocols=["pendle"],
        manual_inputs_json={},
        analysis_depth="standard",
        owner_user_id=owner_user_id,
        visibility="private",
    )
    db.add(analysis)
    db.add(
        ReportModel(
            id=report_id,
            analysis_request_id=analysis.id,
            title="Research report",
            risk_rating=risk_rating,
            summary="Deterministic summary with uncertainty.",
            report_markdown="# report",
            report_json=_report(report_id, strategy, risk_rating).model_dump(mode="json"),
            owner_user_id=owner_user_id,
            visibility="private",
        )
    )


def _persist_lineaged_report(db, owner_user_id: str) -> None:
    source = KnowledgeSourceModel(
        id="source_phase21d",
        owner_user_id=owner_user_id,
        visibility="private",
        source_type="upload",
        title="Private source",
        status="ingested",
        trust_state="approved_for_rag",
    )
    document = KnowledgeDocumentModel(
        id="document_phase21d",
        knowledge_source_id=source.id,
        current_version_id="version_phase21d",
        filename="research.md",
        media_type="text/markdown",
        status="ready",
    )
    version = KnowledgeDocumentVersionModel(
        id="version_phase21d",
        document_id=document.id,
        version_number=1,
        storage_key="phase21d/current",
        checksum="a" * 64,
        size_bytes=1,
        status="ready",
    )
    chunk = KnowledgeChunkModel(
        id="chunk_phase21d",
        document_version_id=version.id,
        chunk_index=0,
        heading_path=["Research"],
        content="Private evidence remains in the source store.",
        content_checksum="c" * 64,
        token_count=6,
        metadata_json={},
    )
    report_id = "report_phase21d_lineage"
    analysis = AnalysisRequestModel(
        id="analysis_phase21d_lineage",
        strategy_description="Lineaged report",
        protocols=["pendle"],
        manual_inputs_json={},
        analysis_depth="standard",
        owner_user_id=owner_user_id,
        visibility="private",
    )
    report = _report(
        report_id,
        "Lineaged strategy",
        "Moderate",
        SourceReference(
            title="Private source",
            source_type="upload",
            citation_lineage=CitationLineageReference(
                citation_id="citation_phase21d",
                source_id=source.id,
                source_title=source.title,
                document_id=document.id,
                document_version_id=version.id,
                document_version_checksum=version.checksum,
                chunk_id=chunk.id,
                chunk_checksum=chunk.content_checksum,
                heading_path=["Research"],
            ),
        ),
    )
    db.add_all([source, document, version, chunk, analysis])
    db.add(
        ReportModel(
            id=report_id,
            analysis_request_id=analysis.id,
            title="Lineaged report",
            risk_rating="Moderate",
            summary=report.executive_summary,
            report_markdown="# report",
            report_json=report.model_dump(mode="json"),
            owner_user_id=owner_user_id,
            visibility="private",
        )
    )


def _report(report_id: str, strategy: str, risk_rating: str, source: SourceReference | None = None) -> ReportResponse:
    return ReportResponse(
        report_id=report_id,
        risk_rating=risk_rating,
        executive_summary="Deterministic summary with uncertainty.",
        strategy_description=strategy,
        protocols=["pendle"],
        assumptions=["Inputs may change."],
        missing_data=["Current utilization"],
        sections=[ReportSection(title="Risk Analysis", content="Deterministic risk section.")],
        sources=[source or SourceReference(title="Synthetic source", source_type="public_doc")],
        disclaimer="Educational research only.",
    )
