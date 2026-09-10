from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from threading import Barrier
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.auth.service import create_user, user_context
from app.core.config import get_settings
from app.db.session import create_database_engine
from app.llm.feedback import create_model_feedback, review_model_feedback
from app.llm.feedback_schemas import ModelFeedbackCreateRequest
from app.llm.governance import record_model_run_provenance, record_model_run_quality_evidence
from app.llm.provenance import fallback_report_synthesis_candidate
from app.llm.quality import ModelQualityEvidence
from app.models.analysis_request import AnalysisRequestModel
from app.models.model_governance import ModelFeedbackModel, ModelRunQualityEvidenceModel
from app.models.organization import OrganizationMembershipModel, OrganizationModel
from app.models.report import ReportModel
from app.models.user import UserModel
from app.schemas.reports import ReportResponse, ReportSection, SourceReference


pytestmark = pytest.mark.postgres_integration


@pytest.fixture(scope="module")
def postgres_sessions() -> sessionmaker:
    if os.getenv("RUN_POSTGRES_INTEGRATION") != "true":
        pytest.skip("Phase 21C PostgreSQL tests require RUN_POSTGRES_INTEGRATION=true")
    engine = create_database_engine()
    if engine.dialect.name != "postgresql":
        pytest.skip("Phase 21C PostgreSQL tests require a PostgreSQL DATABASE_URL")
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


def test_postgres_feedback_tenant_isolation_and_review_lock_are_exactly_once(postgres_sessions: sessionmaker) -> None:
    suffix = uuid4().hex[:12]
    with postgres_sessions() as db:
        owner = create_user(db, f"phase21c-owner-{suffix}@example.test")
        member = create_user(db, f"phase21c-member-{suffix}@example.test")
        outsider = create_user(db, f"phase21c-outsider-{suffix}@example.test")
        admin = create_user(db, f"phase21c-admin-{suffix}@example.test", role="admin")
        organization = OrganizationModel(
            id=f"org_phase21c_pg_{suffix}",
            name=f"Phase 21C PostgreSQL {suffix}",
            slug=f"phase-21c-pg-{suffix}",
            status="active",
            created_by_user_id=owner.id,
        )
        db.add(organization)
        db.flush()
        db.add_all(
            [
                OrganizationMembershipModel(
                    id=f"membership_phase21c_pg_owner_{suffix}",
                    organization_id=organization.id,
                    user_id=owner.id,
                    role="owner",
                    status="active",
                ),
                OrganizationMembershipModel(
                    id=f"membership_phase21c_pg_member_{suffix}",
                    organization_id=organization.id,
                    user_id=member.id,
                    role="member",
                    status="active",
                ),
            ]
        )
        report = _persist_report(db, suffix, owner.id)
        organization_report = _persist_report(db, f"organization_{suffix}", owner.id, organization.id)
        feedback = create_model_feedback(
            db,
            user_context(owner),
            report.id,
            ModelFeedbackCreateRequest(category="bad_citation", comment="Private feedback remains in the tenant row."),
        )
        organization_feedback = create_model_feedback(
            db,
            user_context(member),
            organization_report.id,
            ModelFeedbackCreateRequest(category="unclear"),
        )
        assert db.get(ModelFeedbackModel, organization_feedback.id).organization_id == organization.id
        with pytest.raises(HTTPException) as exc_info:
            create_model_feedback(
                db,
                user_context(outsider),
                organization_report.id,
                ModelFeedbackCreateRequest(category="helpful"),
            )
        assert exc_info.value.status_code == 404
        owner_id, admin_id, feedback_id = owner.id, admin.id, feedback.id

    barrier = Barrier(2)

    def approve() -> str:
        with postgres_sessions() as db:
            actor = user_context(db.get(UserModel, admin_id))
            barrier.wait(timeout=10)
            return review_model_feedback(db, actor, feedback_id, "approved_for_dataset").review_state

    with ThreadPoolExecutor(max_workers=2) as executor:
        assert list(executor.map(lambda _value: approve(), range(2))) == ["approved_for_dataset", "approved_for_dataset"]
    with postgres_sessions() as db:
        stored = db.get(ModelFeedbackModel, feedback_id)
        assert stored is not None
        assert stored.owner_user_id == owner_id
        assert stored.review_state == "approved_for_dataset"
        assert stored.dataset_review_reference and stored.dataset_review_reference.startswith("feedback_case_")


def test_postgres_quality_evidence_is_immutable_and_linked_once(postgres_sessions: sessionmaker) -> None:
    suffix = uuid4().hex[:12]
    with postgres_sessions() as db:
        owner = create_user(db, f"phase21c-quality-owner-{suffix}@example.test")
        report_model = _persist_report(db, f"quality_{suffix}", owner.id)
        report = _report(report_model.id)
        model_run = record_model_run_provenance(
            db,
            report_id=report.report_id,
            candidate=fallback_report_synthesis_candidate(
                report,
                scope_class="private",
                outcome="disabled",
                validation_result="not_run",
                fallback_reason="synthesis_disabled",
            ),
            owner_user_id=owner.id,
            organization_id=None,
            anonymous_session_id=None,
        )
        quality = ModelQualityEvidence(
            citation_consistency=True,
            unsupported_claim_count=0,
            missing_source_honesty=True,
            uncertainty_preserved=True,
            source_instruction_flag_count=0,
            poisoning_detected=False,
            unsafe_language_violation=False,
            deterministic_integrity=True,
            overall_quality_pass=True,
            reason_code=None,
        )
        evidence = record_model_run_quality_evidence(db, model_run=model_run, quality=quality)
        assert evidence is not None
        assert record_model_run_quality_evidence(db, model_run=model_run, quality=quality).id == evidence.id
        db.commit()
        evidence.overall_quality_pass = False
        with pytest.raises(ValueError, match="immutable"):
            db.commit()
        db.rollback()
        assert db.scalars(
            select(ModelRunQualityEvidenceModel).where(
                ModelRunQualityEvidenceModel.model_run_provenance_id == model_run.id
            )
        ).one().overall_quality_pass is True


def _persist_report(db, suffix: str, owner_user_id: str, organization_id: str | None = None) -> ReportModel:
    report_id = f"report_phase21c_pg_{suffix}"
    analysis = AnalysisRequestModel(
        id=f"analysis_phase21c_pg_{suffix}",
        strategy_description="PostgreSQL tenant report.",
        protocols=["pendle"],
        manual_inputs_json={},
        analysis_depth="standard",
        owner_user_id=owner_user_id,
        organization_id=organization_id,
        visibility="organization" if organization_id else "private",
    )
    report = ReportModel(
        id=report_id,
        analysis_request_id=analysis.id,
        title="Phase 21C PostgreSQL report",
        risk_rating="Aggressive",
        summary="Private PostgreSQL summary",
        report_markdown="# report",
        report_json=_report(report_id).model_dump(mode="json"),
        owner_user_id=owner_user_id,
        organization_id=organization_id,
        visibility="organization" if organization_id else "private",
    )
    db.add_all([analysis, report])
    db.commit()
    return report


def _report(report_id: str) -> ReportResponse:
    return ReportResponse(
        report_id=report_id,
        risk_rating="Aggressive",
        executive_summary="Deterministic summary with uncertainty.",
        strategy_description="PostgreSQL tenant report.",
        protocols=["pendle"],
        assumptions=["Deterministic workflow."],
        missing_data=["Synthetic missing field"],
        sections=[
            ReportSection(title="Strategy Description", content="PostgreSQL tenant report."),
            ReportSection(title="Protocols Involved", content="pendle"),
            ReportSection(title="Strategy Mechanics", content="Deterministic mechanics."),
            ReportSection(title="Yield Source", content="Deterministic yield source."),
            ReportSection(title="Market Data Summary", content="Partial market data."),
            ReportSection(title="Key Assumptions", content="Deterministic assumptions."),
            ReportSection(title="Risk Analysis", content="Deterministic risk analysis."),
            ReportSection(title="Stress Scenarios", content="Synthetic stress scenario."),
            ReportSection(title="Simulation Summary", content="Synthetic simulation summary."),
            ReportSection(title="Exit Plan", content="Educational review only."),
            ReportSection(title="Monitoring Checklist", content="Synthetic monitoring checklist."),
            ReportSection(title="Risk Rating", content="Aggressive deterministic rating."),
            ReportSection(title="Missing Data and Uncertainty", content="Synthetic missing field."),
            ReportSection(title="Sources", content="Synthetic source."),
            ReportSection(title="Disclaimer", content="Educational synthetic disclaimer."),
        ],
        sources=[SourceReference(title="Synthetic source", source_type="public_doc", url="https://example.test/source")],
        disclaimer="Educational synthetic disclaimer.",
    )
