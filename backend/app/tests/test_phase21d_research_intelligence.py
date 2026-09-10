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
from app.models.model_governance import ModelPromptVersionModel, ModelRunProvenanceModel
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
        json={
            "statement": "Buy only after a maturity review.",
            "evidence_references": [{"unverified_reference": "User research note"}],
            "expected_thesis_revision": 1,
        },
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
            "expected_thesis_revision": 2,
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
            "expected_thesis_revision": 3,
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


def test_first_legacy_patch_preserves_exact_baseline_before_mutation(research_client) -> None:
    client, Session, identities = research_client
    headers = {"Authorization": "Bearer phase21d-owner-token"}
    original = {
        "title": "Original legacy thesis",
        "strategy_text": "The exact legacy strategy must become the first immutable revision.",
        "protocols": ["pendle", "morpho"],
        "assumptions": {"legacy": "original"},
    }
    with Session() as db:
        db.add(
            SavedThesisModel(
                id="thesis_phase21d_first_patch",
                owner_user_id=identities["owner"],
                title=original["title"],
                strategy_text=original["strategy_text"],
                protocols=original["protocols"],
                assumptions_json=original["assumptions"],
                visibility="private",
            )
        )
        db.commit()
    updated = client.patch(
        "/api/theses/thesis_phase21d_first_patch",
        headers=headers,
        json={"title": "Updated legacy thesis", "change_reason": "First Phase 21D mutation"},
    )
    assert updated.status_code == 200
    history = client.get("/api/theses/thesis_phase21d_first_patch/history", headers=headers)
    assert history.status_code == 200
    items = history.json()["items"]
    assert [item["revision_number"] for item in items] == [1, 2]
    assert items[0]["origin"] == "legacy_baseline"
    assert items[0]["title"] == original["title"]
    assert items[0]["strategy_text"] == original["strategy_text"]
    assert items[0]["protocols"] == original["protocols"]
    assert items[0]["assumptions_snapshot"] == original["assumptions"]
    assert items[1]["title"] == "Updated legacy thesis"


def test_evidence_scope_is_bound_to_destination_thesis_and_rejections_do_not_persist(research_client) -> None:
    client, Session, identities = research_client
    headers = {"Authorization": "Bearer phase21d-owner-token"}
    with Session() as db:
        second_org = OrganizationModel(
            id="org_phase21d_second",
            name="Second Phase 21D organization",
            slug="phase-21d-second-organization",
            status="active",
            created_by_user_id=identities["owner"],
        )
        db.add_all([
            second_org,
            OrganizationMembershipModel(
                id="membership_phase21d_second_owner",
                organization_id=second_org.id,
                user_id=identities["owner"],
                role="owner",
                status="active",
            ),
        ])
        _persist_scoped_lineaged_report(db, "report_phase21d_private_evidence", identities["owner"])
        _persist_scoped_lineaged_report(db, "report_phase21d_org_a_evidence", identities["owner"], "org_phase21d")
        _persist_scoped_lineaged_report(db, "report_phase21d_org_b_evidence", identities["owner"], second_org.id)
        db.commit()

    private_thesis = _create_thesis(client, headers, "Private evidence thesis")
    allowed_private = client.post(
        f"/api/theses/{private_thesis}/assumptions",
        headers=headers,
        json=_evidence_assumption("report_phase21d_private_evidence", "citation_report_phase21d_private_evidence", 1),
    )
    assert allowed_private.status_code == 200
    denied_private_org = client.post(
        f"/api/theses/{private_thesis}/assumptions",
        headers=headers,
        json=_evidence_assumption("report_phase21d_org_a_evidence", "citation_report_phase21d_org_a_evidence", 2),
    )
    assert denied_private_org.status_code == 404
    assert "citation" not in denied_private_org.text.lower()

    organization_thesis = _create_thesis(client, headers, "Organization evidence thesis", organization_id="org_phase21d")
    allowed_org = client.post(
        f"/api/theses/{organization_thesis}/assumptions",
        headers=headers,
        json=_evidence_assumption("report_phase21d_org_a_evidence", "citation_report_phase21d_org_a_evidence", 1),
    )
    assert allowed_org.status_code == 200
    for report_id, citation_id in [
        ("report_phase21d_org_b_evidence", "citation_report_phase21d_org_b_evidence"),
        ("report_phase21d_private_evidence", "citation_report_phase21d_private_evidence"),
    ]:
        denied = client.post(
            f"/api/theses/{organization_thesis}/assumptions",
            headers=headers,
            json=_evidence_assumption(report_id, citation_id, 2),
        )
        assert denied.status_code == 404
        assert report_id not in denied.text
    denied_catalyst = client.post(
        f"/api/theses/{organization_thesis}/catalysts",
        headers=headers,
        json={
            "title": "Foreign organization event",
            "date_precision": "unknown",
            "expected_thesis_revision": 2,
            "evidence_references": [{"report_id": "report_phase21d_org_b_evidence", "citation_ids": ["citation_report_phase21d_org_b_evidence"]}],
        },
    )
    assert denied_catalyst.status_code == 404
    with Session() as db:
        rows = db.scalars(
            select(ThesisAssumptionModel)
            .where(ThesisAssumptionModel.thesis_id.in_((private_thesis, organization_thesis)))
        ).all()
        assert len(rows) == 2
        persisted = str([item.evidence_references for item in rows])
        assert "report_phase21d_org_b_evidence" not in persisted
        assert "report_phase21d_private_evidence" in persisted
        assert "report_phase21d_org_a_evidence" in persisted


def test_revisions_pin_exact_assumption_versions_and_enforce_thesis_revision_conflicts(research_client) -> None:
    client, Session, _ = research_client
    headers = {"Authorization": "Bearer phase21d-owner-token"}
    thesis_id = _create_thesis(client, headers, "Pinned assumption thesis")
    created = client.post(
        f"/api/theses/{thesis_id}/assumptions",
        headers=headers,
        json={"statement": "The original assumption is recorded.", "expected_thesis_revision": 1},
    )
    assert created.status_code == 200
    assumption_id = created.json()["id"]
    revised = client.patch(
        f"/api/theses/{thesis_id}/assumptions/{assumption_id}",
        headers=headers,
        json={
            "statement": "The later assumption supersedes the original.",
            "state": "weakened",
            "expected_revision": 1,
            "expected_thesis_revision": 2,
        },
    )
    assert revised.status_code == 200
    history = client.get(f"/api/theses/{thesis_id}/history", headers=headers).json()["items"]
    first_assumption_revision = history[1]["explicit_assumption_versions"][0]
    second_assumption_revision = history[2]["explicit_assumption_versions"][0]
    assert first_assumption_revision["assumption_id"] == second_assumption_revision["assumption_id"] == assumption_id
    assert first_assumption_revision["assumption_revision_number"] == 1
    assert second_assumption_revision["assumption_revision_number"] == 2
    assert first_assumption_revision["assumption_record_id"] != second_assumption_revision["assumption_record_id"]

    missing_expected = client.patch(
        f"/api/theses/{thesis_id}", headers=headers, json={"title": "Missing current revision"}
    )
    assert missing_expected.status_code == 422
    stale_status = client.post(
        f"/api/theses/{thesis_id}/status", headers=headers, json={"status": "challenged", "expected_revision": 1}
    )
    assert stale_status.status_code == 409
    retry = client.patch(
        f"/api/theses/{thesis_id}",
        headers=headers,
        json={"title": "Saved after refresh", "expected_revision": 3},
    )
    assert retry.status_code == 200
    with Session() as db:
        records = db.scalars(
            select(ThesisAssumptionModel)
            .where(ThesisAssumptionModel.thesis_id == thesis_id)
            .where(ThesisAssumptionModel.assumption_id == assumption_id)
            .order_by(ThesisAssumptionModel.revision_number)
        ).all()
        assert [item.id for item in records] == [
            first_assumption_revision["assumption_record_id"],
            second_assumption_revision["assumption_record_id"],
        ]


def test_report_comparison_content_origin_uses_durable_synthesis_provenance(research_client) -> None:
    client, Session, identities = research_client
    headers = {"Authorization": "Bearer phase21d-owner-token"}
    with Session() as db:
        _persist_scoped_lineaged_report(db, "report_phase21d_model_left", identities["owner"], sections=_comparison_sections("model left"))
        _persist_scoped_lineaged_report(db, "report_phase21d_model_right", identities["owner"], sections=_comparison_sections("model right"))
        _persist_scoped_lineaged_report(db, "report_phase21d_fallback", identities["owner"], sections=_comparison_sections("fallback"))
        _persist_scoped_lineaged_report(db, "report_phase21d_legacy_provenance", identities["owner"], sections=_comparison_sections("legacy"))
        _record_synthesis_provenance(db, "report_phase21d_model_left", identities["owner"], outcome="succeeded", validation_result="accepted")
        _record_synthesis_provenance(db, "report_phase21d_model_right", identities["owner"], outcome="succeeded", validation_result="accepted")
        _record_synthesis_provenance(db, "report_phase21d_fallback", identities["owner"], outcome="validation_fallback", validation_result="schema_invalid")
        db.commit()

    deterministic = client.post(
        "/api/reports/compare", headers=headers, json={"left_report_id": "report_phase21d_left", "right_report_id": "report_phase21d_right"}
    )
    assert deterministic.status_code == 200
    assert deterministic.json()["changes"]["risk_rating"]["left_content_origin"] == "deterministic"
    assert deterministic.json()["changes"]["missing_data"]["left_content_origin"] == "deterministic"
    assert deterministic.json()["changes"]["sources"]["left_content_origin"] == "deterministic"
    assert deterministic.json()["changes"]["comparison_provenance"]["computation_origin"] == "deterministic"
    model_fallback = client.post(
        "/api/reports/compare", headers=headers, json={"left_report_id": "report_phase21d_model_left", "right_report_id": "report_phase21d_fallback"}
    )
    assert model_fallback.status_code == 200
    model_section = model_fallback.json()["changes"]["sections"]["Strategy Mechanics"]
    assert model_section["left_content_origin"] == "model_assisted"
    assert model_section["right_content_origin"] == "deterministic_fallback"
    assert model_fallback.json()["changes"]["risk_rating"]["left_content_origin"] == "deterministic"
    model_model = client.post(
        "/api/reports/compare", headers=headers, json={"left_report_id": "report_phase21d_model_left", "right_report_id": "report_phase21d_model_right"}
    )
    assert model_model.json()["changes"]["sections"]["Strategy Mechanics"]["right_content_origin"] == "model_assisted"
    legacy = client.post(
        "/api/reports/compare", headers=headers, json={"left_report_id": "report_phase21d_legacy_provenance", "right_report_id": "report_phase21d_fallback"}
    )
    assert legacy.json()["changes"]["sections"]["Strategy Mechanics"]["left_content_origin"] == "unknown"


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


def _create_thesis(client: TestClient, headers: dict[str, str], title: str, organization_id: str | None = None) -> str:
    payload = {
        "title": title,
        "strategy_text": "Research scope must remain bound to the durable destination thesis.",
        "protocols": ["pendle"],
        "assumptions": {},
        "visibility": "organization" if organization_id else "private",
    }
    if organization_id:
        payload["organization_id"] = organization_id
    created = client.post("/api/theses", headers=headers, json=payload)
    assert created.status_code == 200
    return created.json()["id"]


def _evidence_assumption(report_id: str, citation_id: str, expected_thesis_revision: int) -> dict:
    return {
        "statement": "The cited evidence is explicitly attached to this thesis scope.",
        "expected_thesis_revision": expected_thesis_revision,
        "evidence_references": [{"report_id": report_id, "citation_ids": [citation_id]}],
    }


def _comparison_sections(label: str) -> list[ReportSection]:
    return [
        ReportSection(title="Strategy Mechanics", content=f"{label} mechanics."),
        ReportSection(title="Risk Analysis", content=f"{label} deterministic risk."),
    ]


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


def _persist_scoped_lineaged_report(
    db,
    report_id: str,
    owner_user_id: str,
    organization_id: str | None = None,
    sections: list[ReportSection] | None = None,
) -> None:
    visibility = "organization" if organization_id else "private"
    analysis = AnalysisRequestModel(
        id=f"analysis_{report_id}",
        strategy_description=f"Scoped evidence for {report_id}",
        protocols=["pendle"],
        manual_inputs_json={},
        analysis_depth="standard",
        owner_user_id=owner_user_id,
        organization_id=organization_id,
        visibility=visibility,
    )
    source = SourceReference(
        title="Scoped durable evidence",
        source_type="knowledge_base",
        citation_lineage=CitationLineageReference(
            citation_id=f"citation_{report_id}",
            source_id=f"source_{report_id}",
            source_title="Scoped durable evidence",
            document_id=f"document_{report_id}",
            document_version_id=f"version_{report_id}",
            document_version_checksum="a" * 64,
            chunk_id=f"chunk_{report_id}",
            chunk_checksum="b" * 64,
            heading_path=["Evidence"],
        ),
    )
    report = _report(report_id, f"Scoped strategy {report_id}", "Moderate", source, sections=sections)
    db.add_all([
        analysis,
        ReportModel(
            id=report_id,
            analysis_request_id=analysis.id,
            title="Scoped research report",
            risk_rating=report.risk_rating,
            summary=report.executive_summary,
            report_markdown="# scoped report",
            report_json=report.model_dump(mode="json"),
            owner_user_id=owner_user_id,
            organization_id=organization_id,
            visibility=visibility,
        ),
    ])


def _record_synthesis_provenance(
    db,
    report_id: str,
    owner_user_id: str,
    *,
    outcome: str,
    validation_result: str,
) -> None:
    prompt = db.get(ModelPromptVersionModel, "prompt_phase21d_comparison")
    if prompt is None:
        prompt = ModelPromptVersionModel(
            id="prompt_phase21d_comparison",
            task_key="report_synthesis",
            task_version="v1",
            prompt_version="phase21d.comparison.v1",
            output_schema_version="report_synthesis.output.v1",
            safety_policy_version="report_synthesis.safety.v2",
            prompt_checksum="d" * 64,
        )
        db.add(prompt)
        db.flush()
    db.add(
        ModelRunProvenanceModel(
            id=f"run_{report_id}",
            report_id=report_id,
            task_key="report_synthesis",
            task_version="v1",
            prompt_version_id=prompt.id,
            owner_user_id=owner_user_id,
            scope_class="private",
            deterministic_input_checksum="e" * 64,
            retrieval_source_count=0,
            validation_result=validation_result,
            outcome=outcome,
            fallback_reason="synthesis_disabled" if outcome != "succeeded" else None,
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


def _report(
    report_id: str,
    strategy: str,
    risk_rating: str,
    source: SourceReference | None = None,
    *,
    sections: list[ReportSection] | None = None,
) -> ReportResponse:
    return ReportResponse(
        report_id=report_id,
        risk_rating=risk_rating,
        executive_summary="Deterministic summary with uncertainty.",
        strategy_description=strategy,
        protocols=["pendle"],
        assumptions=["Inputs may change."],
        missing_data=["Current utilization"],
        sections=sections or [ReportSection(title="Risk Analysis", content="Deterministic risk section.")],
        sources=[source or SourceReference(title="Synthetic source", source_type="public_doc")],
        disclaimer="Educational research only.",
    )
