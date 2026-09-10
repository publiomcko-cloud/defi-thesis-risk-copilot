from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from app.auth.service import create_user, user_context
from app.db.session import create_database_engine
from app.models.analysis_request import AnalysisRequestModel
from app.models.report import ReportModel
from app.models.research_intelligence import ResearchReportComparisonModel, ThesisAssumptionModel, ThesisRevisionModel
from app.models.saved_thesis import SavedThesisModel
from app.models.user import UserModel
from app.research_intelligence.schemas import (
    ReportComparisonRequest,
    ResearchAssumptionCreateRequest,
    ResearchAssumptionUpdateRequest,
)
from app.research_intelligence.service import (
    append_material_revision,
    compare_reports,
    create_assumption,
    create_initial_revision,
    list_history,
    update_assumption,
)
from app.schemas.reports import ReportResponse, ReportSection, SourceReference


pytestmark = pytest.mark.postgres_integration


@pytest.fixture(scope="module")
def postgres_sessions() -> sessionmaker:
    if os.getenv("RUN_POSTGRES_INTEGRATION") != "true":
        pytest.skip("Phase 21D PostgreSQL tests require RUN_POSTGRES_INTEGRATION=true")
    engine = create_database_engine()
    if engine.dialect.name != "postgresql":
        pytest.skip("Phase 21D PostgreSQL tests require a PostgreSQL DATABASE_URL")
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


def test_postgres_thesis_revision_and_assumption_heads_serialise_without_lost_updates(postgres_sessions: sessionmaker) -> None:
    suffix = uuid4().hex[:12]
    with postgres_sessions() as db:
        user = create_user(db, f"phase21d-concurrency-{suffix}@example.test")
        thesis = SavedThesisModel(
            id=f"thesis_phase21d_pg_{suffix}",
            owner_user_id=user.id,
            title="PostgreSQL research thesis",
            strategy_text="Concurrent revision authority must be database serialized.",
            protocols=["pendle"],
            assumptions_json={"legacy": "unchanged"},
            visibility="private",
        )
        db.add(thesis)
        create_initial_revision(db, thesis, user.id)
        db.commit()
        user_id, thesis_id = user.id, thesis.id

    revision_barrier = Barrier(2)

    def append_revision() -> int:
        with postgres_sessions() as db:
            revision_barrier.wait(timeout=10)
            thesis = db.execute(
                select(SavedThesisModel).where(SavedThesisModel.id == thesis_id).with_for_update()
            ).scalars().one()
            record = append_material_revision(
                db,
                thesis,
                actor_user_id=user_id,
                change_reason="Concurrent revision test",
            )
            db.commit()
            return record.revision_number

    with ThreadPoolExecutor(max_workers=2) as executor:
        numbers = list(executor.map(lambda _value: append_revision(), range(2)))
    assert sorted(numbers) == [2, 3]

    with postgres_sessions() as db:
        actor = user_context(db.get(UserModel, user_id))
        created = create_assumption(
            db,
            actor,
            thesis_id,
            ResearchAssumptionCreateRequest(statement="The documented maturity remains applicable."),
        )
        assumption_id = created.id

    assumption_barrier = Barrier(2)

    def revise_assumption() -> int:
        with postgres_sessions() as db:
            actor = user_context(db.get(UserModel, user_id))
            assumption_barrier.wait(timeout=10)
            try:
                update_assumption(
                    db,
                    actor,
                    thesis_id,
                    assumption_id,
                    ResearchAssumptionUpdateRequest(
                        statement="The maturity evidence was reviewed.",
                        state="weakened",
                        expected_revision=1,
                    ),
                )
                return 200
            except HTTPException as exc:
                db.rollback()
                return exc.status_code

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(lambda _value: revise_assumption(), range(2)))
    assert sorted(outcomes) == [200, 409]
    with postgres_sessions() as db:
        versions = db.scalars(
            select(ThesisAssumptionModel)
            .where(ThesisAssumptionModel.thesis_id == thesis_id)
            .where(ThesisAssumptionModel.assumption_id == assumption_id)
            .order_by(ThesisAssumptionModel.revision_number)
        ).all()
        assert [item.revision_number for item in versions] == [1, 2]
        assert len(db.scalars(select(ThesisRevisionModel).where(ThesisRevisionModel.thesis_id == thesis_id)).all()) >= 5


def test_postgres_legacy_baseline_initialization_is_idempotent_under_concurrent_reads(postgres_sessions: sessionmaker) -> None:
    suffix = uuid4().hex[:12]
    with postgres_sessions() as db:
        user = create_user(db, f"phase21d-baseline-{suffix}@example.test")
        thesis = SavedThesisModel(
            id=f"thesis_phase21d_baseline_{suffix}",
            owner_user_id=user.id,
            title="Legacy baseline thesis",
            strategy_text="The saved content must remain unchanged while history starts.",
            protocols=["pendle"],
            assumptions_json={"legacy": "exact"},
            visibility="private",
        )
        db.add(thesis)
        db.commit()
        user_id, thesis_id = user.id, thesis.id
    barrier = Barrier(2)

    def read_history() -> int:
        with postgres_sessions() as db:
            actor = user_context(db.get(UserModel, user_id))
            barrier.wait(timeout=10)
            return len(list_history(db, actor, thesis_id).items)

    with ThreadPoolExecutor(max_workers=2) as executor:
        assert list(executor.map(lambda _value: read_history(), range(2))) == [1, 1]
    with postgres_sessions() as db:
        rows = db.scalars(select(ThesisRevisionModel).where(ThesisRevisionModel.thesis_id == thesis_id)).all()
        assert len(rows) == 1
        assert rows[0].origin == "legacy_baseline"


def test_postgres_report_comparison_unique_input_authority(postgres_sessions: sessionmaker) -> None:
    suffix = uuid4().hex[:12]
    with postgres_sessions() as db:
        user = create_user(db, f"phase21d-comparison-{suffix}@example.test")
        _persist_report(db, f"report_phase21d_pg_left_{suffix}", user.id, "Left deterministic strategy", "Moderate")
        _persist_report(db, f"report_phase21d_pg_right_{suffix}", user.id, "Right deterministic strategy", "Aggressive")
        db.commit()
        user_id = user.id
    left_id, right_id = f"report_phase21d_pg_left_{suffix}", f"report_phase21d_pg_right_{suffix}"
    barrier = Barrier(2)

    def compare() -> str:
        with postgres_sessions() as db:
            actor = user_context(db.get(UserModel, user_id))
            barrier.wait(timeout=10)
            return compare_reports(db, actor, ReportComparisonRequest(left_report_id=left_id, right_report_id=right_id)).id

    with ThreadPoolExecutor(max_workers=2) as executor:
        comparison_ids = list(executor.map(lambda _value: compare(), range(2)))
    assert len(set(comparison_ids)) == 1
    with postgres_sessions() as db:
        rows = db.scalars(
            select(ResearchReportComparisonModel)
            .where(ResearchReportComparisonModel.left_report_id == left_id)
            .where(ResearchReportComparisonModel.right_report_id == right_id)
        ).all()
        assert len(rows) == 1


def _persist_report(db, report_id: str, owner_user_id: str, strategy: str, rating: str) -> None:
    analysis = AnalysisRequestModel(
        id=f"analysis_{report_id}",
        strategy_description=strategy,
        protocols=["pendle"],
        manual_inputs_json={},
        analysis_depth="standard",
        owner_user_id=owner_user_id,
        visibility="private",
    )
    report = ReportResponse(
        report_id=report_id,
        risk_rating=rating,
        executive_summary="Deterministic research summary.",
        strategy_description=strategy,
        protocols=["pendle"],
        assumptions=["Inputs are explicit."],
        missing_data=["Current utilization"],
        sections=[ReportSection(title="Risk Analysis", content="Deterministic section.")],
        sources=[SourceReference(title="Synthetic source", source_type="public_doc")],
        disclaimer="Educational research only.",
    )
    db.add_all([
        analysis,
        ReportModel(
            id=report_id,
            analysis_request_id=analysis.id,
            title="Phase 21D report",
            risk_rating=rating,
            summary=report.executive_summary,
            report_markdown="# report",
            report_json=report.model_dump(mode="json"),
            owner_user_id=owner_user_id,
            visibility="private",
        ),
    ])
