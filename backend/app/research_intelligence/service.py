from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.policies import READ_ORG_ROLES, can_read_resource, has_org_role
from app.auth.schemas import UserContext
from app.models.knowledge import (
    KnowledgeChunkModel,
    KnowledgeDocumentModel,
    KnowledgeDocumentVersionModel,
    KnowledgeSourceModel,
)
from app.models.model_governance import ModelRunProvenanceModel
from app.models.report import ReportModel
from app.models.research_intelligence import (
    ResearchReportComparisonModel,
    ThesisAssumptionHeadModel,
    ThesisAssumptionModel,
    ThesisCatalystModel,
    ThesisRevisionModel,
)
from app.models.saved_thesis import SavedThesisModel
from app.research_intelligence.schemas import (
    CatalystCreateRequest,
    CatalystResponse,
    CatalystUpdateRequest,
    MonitoringQuestionsResponse,
    ReportComparisonRequest,
    ReportComparisonResponse,
    ResearchAssumptionCreateRequest,
    ResearchAssumptionResponse,
    ResearchAssumptionUpdateRequest,
    ScenarioComparisonRequest,
    ScenarioComparisonResponse,
    SourceStalenessResponse,
    ThesisHistoryResponse,
    ThesisRevisionResponse,
    ThesisStatusUpdateRequest,
)
from app.schemas.reports import ReportResponse, SourceReference
from app.llm.prompts import SYNTHESIZABLE_SECTION_TITLES
from app.simulation.simulator import SIMULATION_DISCLAIMER, run_strategy_simulation
from app.theses.policies import can_read_saved_thesis, can_update_saved_thesis


RESEARCH_COMPARISON_SCHEMA = "research_comparison.v1"


def ensure_baseline_revision(db: Session, thesis: SavedThesisModel) -> ThesisRevisionModel:
    """Create exactly one faithful local baseline for a pre-21D thesis."""

    existing = db.execute(
        select(ThesisRevisionModel)
        .where(ThesisRevisionModel.thesis_id == thesis.id)
        .order_by(ThesisRevisionModel.revision_number.desc())
        .limit(1)
    ).scalars().first()
    if existing is not None:
        return existing
    return _append_revision(
        db,
        thesis,
        actor_user_id=thesis.owner_user_id,
        status="draft",
        origin="legacy_baseline",
        change_reason="Pre-21D thesis baseline",
    )


def create_initial_revision(db: Session, thesis: SavedThesisModel, actor_user_id: str) -> ThesisRevisionModel:
    # SQLAlchemy has no relationship edge between these independent mappings;
    # persist the parent explicitly before the immutable child on PostgreSQL.
    db.flush()
    return _append_revision(
        db,
        thesis,
        actor_user_id=actor_user_id,
        status="draft",
        origin="user_recorded",
        change_reason="Thesis created",
    )


def append_material_revision(
    db: Session,
    thesis: SavedThesisModel,
    *,
    actor_user_id: str,
    status: str | None = None,
    change_reason: str | None,
    expected_revision: int | None = None,
) -> ThesisRevisionModel:
    current = ensure_baseline_revision(db, thesis)
    if expected_revision is not None and current.revision_number != expected_revision:
        raise HTTPException(status_code=409, detail="Thesis revision changed; refresh before updating")
    return _append_revision(
        db,
        thesis,
        actor_user_id=actor_user_id,
        status=status or current.status,
        origin="user_recorded",
        change_reason=change_reason,
    )


def prepare_material_mutation(
    db: Session,
    thesis: SavedThesisModel,
    *,
    expected_revision: int | None,
) -> ThesisRevisionModel:
    """Establish the immutable baseline before any mutable research operation.

    A pre-21D thesis has no research revision for a browser to have observed, so
    its first mutation may omit ``expected_revision``. The locked baseline becomes
    revision 1 and the same transaction appends the requested change as revision 2.
    Once any revision already exists, callers must supply that exact revision.
    """

    prior = db.execute(
        select(ThesisRevisionModel.id)
        .where(ThesisRevisionModel.thesis_id == thesis.id)
        .limit(1)
    ).scalar_one_or_none()
    current = ensure_baseline_revision(db, thesis)
    if prior is not None and expected_revision is None:
        raise HTTPException(status_code=422, detail="expected_revision is required for an existing thesis revision")
    if expected_revision is not None and current.revision_number != expected_revision:
        raise HTTPException(status_code=409, detail="Thesis revision changed; refresh before updating")
    return current


def list_history(db: Session, actor: UserContext, thesis_id: str) -> ThesisHistoryResponse:
    thesis = _locked_authorized_read_thesis(db, actor, thesis_id)
    ensure_baseline_revision(db, thesis)
    db.commit()
    rows = db.execute(
        select(ThesisRevisionModel)
        .where(ThesisRevisionModel.thesis_id == thesis.id)
        .order_by(ThesisRevisionModel.revision_number)
    ).scalars().all()
    return ThesisHistoryResponse(items=[_revision_response(row) for row in rows])


def update_status(
    db: Session,
    actor: UserContext,
    thesis_id: str,
    request: ThesisStatusUpdateRequest,
) -> ThesisRevisionResponse:
    thesis = _locked_authorized_thesis(db, actor, thesis_id)
    prepare_material_mutation(db, thesis, expected_revision=request.expected_revision)
    revision = append_material_revision(
        db,
        thesis,
        actor_user_id=actor.id,
        status=request.status,
        change_reason=request.change_reason or "Thesis status updated",
        expected_revision=request.expected_revision,
    )
    db.commit()
    return _revision_response(revision)


def list_assumptions(db: Session, actor: UserContext, thesis_id: str) -> list[ResearchAssumptionResponse]:
    thesis = _authorized_thesis(db, actor, thesis_id, write=False)
    rows = db.execute(
        select(ThesisAssumptionModel)
        .where(ThesisAssumptionModel.thesis_id == thesis.id)
        .order_by(ThesisAssumptionModel.assumption_id, ThesisAssumptionModel.revision_number)
    ).scalars().all()
    return [_assumption_response(row) for row in rows]


def create_assumption(
    db: Session,
    actor: UserContext,
    thesis_id: str,
    request: ResearchAssumptionCreateRequest,
) -> ResearchAssumptionResponse:
    thesis = _locked_authorized_thesis(db, actor, thesis_id)
    prepare_material_mutation(db, thesis, expected_revision=request.expected_thesis_revision)
    now = datetime.now(UTC)
    assumption_id = f"asm_{uuid4().hex[:12]}"
    record = ThesisAssumptionModel(
        id=f"asmv_{uuid4().hex[:12]}",
        thesis_id=thesis.id,
        assumption_id=assumption_id,
        revision_number=1,
        statement=request.statement,
        state=request.state,
        evidence_references=_resolve_evidence_references(db, actor, thesis, request.evidence_references),
        actor_user_id=actor.id,
        origin="user_recorded",
        created_at=now,
    )
    db.add(record)
    db.flush()
    db.add(
        ThesisAssumptionHeadModel(
            id=f"asmh_{uuid4().hex[:12]}",
            thesis_id=thesis.id,
            assumption_id=assumption_id,
            current_record_id=record.id,
            current_revision_number=1,
            updated_at=now,
        )
    )
    # Sessions intentionally disable autoflush; pin the newly current immutable
    # version before the thesis revision snapshots the head set.
    db.flush()
    append_material_revision(
        db,
        thesis,
        actor_user_id=actor.id,
        change_reason="Assumption recorded",
        expected_revision=request.expected_thesis_revision,
    )
    db.commit()
    return _assumption_response(record)


def update_assumption(
    db: Session,
    actor: UserContext,
    thesis_id: str,
    assumption_id: str,
    request: ResearchAssumptionUpdateRequest,
) -> ResearchAssumptionResponse:
    thesis = _locked_authorized_thesis(db, actor, thesis_id)
    prepare_material_mutation(db, thesis, expected_revision=request.expected_thesis_revision)
    head = db.execute(
        select(ThesisAssumptionHeadModel)
        .where(ThesisAssumptionHeadModel.thesis_id == thesis.id)
        .where(ThesisAssumptionHeadModel.assumption_id == assumption_id)
        .with_for_update()
    ).scalars().one_or_none()
    if head is None:
        raise HTTPException(status_code=404, detail="Assumption not found")
    if head.current_revision_number != request.expected_revision:
        raise HTTPException(status_code=409, detail="Assumption changed; refresh before updating")
    prior = db.get(ThesisAssumptionModel, head.current_record_id)
    if prior is None:
        raise HTTPException(status_code=409, detail="Assumption state is unavailable")
    now = datetime.now(UTC)
    record = ThesisAssumptionModel(
        id=f"asmv_{uuid4().hex[:12]}",
        thesis_id=thesis.id,
        assumption_id=assumption_id,
        revision_number=head.current_revision_number + 1,
        statement=request.statement,
        state=request.state,
        evidence_references=_resolve_evidence_references(db, actor, thesis, request.evidence_references),
        supersedes_record_id=prior.id,
        actor_user_id=actor.id,
        origin="user_recorded",
        created_at=now,
    )
    db.add(record)
    db.flush()
    head.current_record_id = record.id
    head.current_revision_number = record.revision_number
    head.updated_at = now
    db.flush()
    append_material_revision(
        db,
        thesis,
        actor_user_id=actor.id,
        change_reason="Assumption revised",
        expected_revision=request.expected_thesis_revision,
    )
    db.commit()
    return _assumption_response(record)


def list_catalysts(db: Session, actor: UserContext, thesis_id: str) -> list[CatalystResponse]:
    thesis = _authorized_thesis(db, actor, thesis_id, write=False)
    rows = db.execute(
        select(ThesisCatalystModel)
        .where(ThesisCatalystModel.thesis_id == thesis.id)
        .order_by(ThesisCatalystModel.expected_date, ThesisCatalystModel.created_at)
    ).scalars().all()
    return [_catalyst_response(row) for row in rows]


def create_catalyst(
    db: Session,
    actor: UserContext,
    thesis_id: str,
    request: CatalystCreateRequest,
) -> CatalystResponse:
    thesis = _locked_authorized_thesis(db, actor, thesis_id)
    prepare_material_mutation(db, thesis, expected_revision=request.expected_thesis_revision)
    now = datetime.now(UTC)
    record = ThesisCatalystModel(
        id=f"cat_{uuid4().hex[:12]}",
        thesis_id=thesis.id,
        owner_user_id=thesis.owner_user_id,
        organization_id=thesis.organization_id if thesis.visibility == "organization" else None,
        title=request.title,
        description=request.description,
        expected_date=request.expected_date,
        window_start=request.window_start,
        window_end=request.window_end,
        date_precision=request.date_precision,
        status=request.status,
        uncertainty=request.uncertainty,
        evidence_references=_resolve_evidence_references(db, actor, thesis, request.evidence_references),
        revision_number=1,
        actor_user_id=actor.id,
        created_at=now,
        updated_at=now,
    )
    db.add(record)
    append_material_revision(
        db,
        thesis,
        actor_user_id=actor.id,
        change_reason="Catalyst recorded",
        expected_revision=request.expected_thesis_revision,
    )
    db.commit()
    return _catalyst_response(record)


def update_catalyst(
    db: Session,
    actor: UserContext,
    thesis_id: str,
    catalyst_id: str,
    request: CatalystUpdateRequest,
) -> CatalystResponse:
    thesis = _locked_authorized_thesis(db, actor, thesis_id)
    prepare_material_mutation(db, thesis, expected_revision=request.expected_thesis_revision)
    record = db.execute(
        select(ThesisCatalystModel)
        .where(ThesisCatalystModel.id == catalyst_id)
        .where(ThesisCatalystModel.thesis_id == thesis.id)
        .with_for_update()
    ).scalars().one_or_none()
    if record is None:
        raise HTTPException(status_code=404, detail="Catalyst not found")
    if record.revision_number != request.expected_revision:
        raise HTTPException(status_code=409, detail="Catalyst changed; refresh before updating")
    record.title = request.title
    record.description = request.description
    record.expected_date = request.expected_date
    record.window_start = request.window_start
    record.window_end = request.window_end
    record.date_precision = request.date_precision
    record.status = request.status
    record.uncertainty = request.uncertainty
    record.evidence_references = _resolve_evidence_references(db, actor, thesis, request.evidence_references)
    record.revision_number += 1
    record.actor_user_id = actor.id
    record.updated_at = datetime.now(UTC)
    append_material_revision(
        db,
        thesis,
        actor_user_id=actor.id,
        change_reason="Catalyst revised",
        expected_revision=request.expected_thesis_revision,
    )
    db.commit()
    return _catalyst_response(record)


def compare_reports(
    db: Session,
    actor: UserContext,
    request: ReportComparisonRequest,
) -> ReportComparisonResponse:
    left = _authorized_report(db, actor, request.left_report_id)
    right = _authorized_report(db, actor, request.right_report_id)
    scope_class, scope_key, owner_user_id, organization_id = _compatible_report_scope(left, right)
    existing = db.execute(
        select(ResearchReportComparisonModel)
        .where(ResearchReportComparisonModel.left_report_id == left.id)
        .where(ResearchReportComparisonModel.right_report_id == right.id)
        .where(ResearchReportComparisonModel.scope_key == scope_key)
    ).scalars().one_or_none()
    if existing is not None:
        return _comparison_response(existing)
    changes = _deterministic_report_diff(db, left, right)
    left_checksum = _report_checksum(left)
    right_checksum = _report_checksum(right)
    lineage_digest = _checksum({"left": changes["sources"], "right": changes["citation_lineage"]})
    record = ResearchReportComparisonModel(
        id=f"cmp_{uuid4().hex[:12]}",
        left_report_id=left.id,
        right_report_id=right.id,
        left_input_checksum=left_checksum,
        right_input_checksum=right_checksum,
        scope_class=scope_class,
        scope_key=scope_key,
        owner_user_id=owner_user_id,
        organization_id=organization_id,
        schema_version=RESEARCH_COMPARISON_SCHEMA,
        comparison_json=changes,
        lineage_digest=lineage_digest,
        created_at=datetime.now(UTC),
    )
    db.add(record)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        record = db.execute(
            select(ResearchReportComparisonModel)
            .where(ResearchReportComparisonModel.left_report_id == left.id)
            .where(ResearchReportComparisonModel.right_report_id == right.id)
            .where(ResearchReportComparisonModel.scope_key == scope_key)
        ).scalars().one()
    return _comparison_response(record)


def report_staleness(db: Session, actor: UserContext, report_id: str) -> SourceStalenessResponse:
    report = _authorized_report(db, actor, report_id)
    payload = ReportResponse.model_validate(report.report_json)
    items = [_staleness_item(db, index, source) for index, source in enumerate(payload.sources)]
    return SourceStalenessResponse(report_id=report.id, items=items)


def compare_scenarios(request: ScenarioComparisonRequest) -> ScenarioComparisonResponse:
    left = run_strategy_simulation(request.left)
    right = run_strategy_simulation(request.right)
    left_by_type = {item.scenario_type: item for item in left.scenarios}
    right_by_type = {item.scenario_type: item for item in right.scenarios}
    changes: list[dict] = []
    for scenario_type in sorted(set(left_by_type) | set(right_by_type)):
        before = left_by_type.get(scenario_type)
        after = right_by_type.get(scenario_type)
        if before is None or after is None:
            changes.append({"scenario_type": scenario_type, "status": "unknown", "metrics": []})
            continue
        metrics = []
        for key in sorted(set(before.result) | set(after.result)):
            left_value = before.result.get(key)
            right_value = after.result.get(key)
            if left_value is None or right_value is None:
                status = "unknown"
                delta = None
            elif left_value == right_value:
                status = "unchanged"
                delta = 0 if isinstance(left_value, (int, float)) and isinstance(right_value, (int, float)) else None
            else:
                status = "changed"
                delta = right_value - left_value if isinstance(left_value, (int, float)) and isinstance(right_value, (int, float)) else None
            metrics.append({"key": key, "status": status, "left": left_value, "right": right_value, "delta": delta})
        changes.append({"scenario_type": scenario_type, "status": "deterministic", "metrics": metrics})
    return ScenarioComparisonResponse(
        changes=changes,
        missing_data=sorted(set(left.missing_data) | set(right.missing_data)),
        disclaimer=SIMULATION_DISCLAIMER,
    )


def monitoring_questions(
    db: Session,
    actor: UserContext,
    thesis_id: str,
    report_id: str | None = None,
) -> MonitoringQuestionsResponse:
    thesis = _authorized_thesis(db, actor, thesis_id, write=False)
    assumptions = db.execute(
        select(ThesisAssumptionModel)
        .join(ThesisAssumptionHeadModel, ThesisAssumptionHeadModel.current_record_id == ThesisAssumptionModel.id)
        .where(ThesisAssumptionHeadModel.thesis_id == thesis.id)
        .where(ThesisAssumptionModel.state.in_(("active", "weakened")))
        .order_by(ThesisAssumptionModel.created_at)
    ).scalars().all()
    catalysts = db.execute(
        select(ThesisCatalystModel)
        .where(ThesisCatalystModel.thesis_id == thesis.id)
        .where(ThesisCatalystModel.status == "upcoming")
        .order_by(ThesisCatalystModel.expected_date, ThesisCatalystModel.created_at)
    ).scalars().all()
    questions: list[str] = []
    for item in assumptions:
        candidate = f"Has evidence changed the assumption: {item.statement.strip()[:220]}?"
        if _safe_research_question(candidate):
            questions.append(candidate)
        for evidence in item.evidence_references:
            lineage = evidence.get("citation_lineage") if isinstance(evidence, dict) else None
            if isinstance(lineage, dict) and lineage.get("citation_id"):
                questions.append(f"Is the cited evidence {lineage['citation_id']} still current?")
    for item in catalysts:
        candidate = f"Has the catalyst '{item.title}' occurred or changed status?"
        if _safe_research_question(candidate):
            questions.append(candidate)
    if report_id is not None:
        report = _authorized_evidence_report(db, actor, thesis, report_id)
        payload = ReportResponse.model_validate(report.report_json)
        for missing_data in payload.missing_data:
            candidate = f"Is the missing evidence '{missing_data[:180]}' now available from an authoritative source?"
            if _safe_research_question(candidate):
                questions.append(candidate)
        for item in [_staleness_item(db, index, source) for index, source in enumerate(payload.sources)]:
            if item["status"] in {"superseded", "deleted", "unavailable"}:
                citation_id = item.get("citation_id", "source evidence")
                questions.append(f"Has the status of {citation_id} changed, and what remains uncertain?")
    if not questions:
        questions.append("Is the thesis evidence current, and which missing evidence still needs review?")
    return MonitoringQuestionsResponse(
        thesis_id=thesis.id,
        questions=questions[:12],
        uncertainty=["Questions are deterministic research prompts. They do not create schedules, notifications, or trading actions."],
    )


def dispose_research_intelligence_for_thesis(db: Session, thesis_id: str) -> None:
    _delete_thesis_research_rows(db, [thesis_id])


def dispose_research_intelligence_for_account(db: Session, owner_user_id: str) -> None:
    thesis_ids = _private_thesis_ids_for_account(db, owner_user_id)
    db.execute(
        delete(ResearchReportComparisonModel)
        .where(ResearchReportComparisonModel.owner_user_id == owner_user_id)
        .where(ResearchReportComparisonModel.scope_class == "private")
        .where(ResearchReportComparisonModel.scope_key == f"private:{owner_user_id}")
        .where(ResearchReportComparisonModel.organization_id.is_(None))
    )
    _delete_thesis_research_rows(db, thesis_ids)


def dispose_research_intelligence_for_organization(db: Session, organization_id: str) -> None:
    thesis_ids = list(
        db.scalars(
            select(SavedThesisModel.id)
            .where(SavedThesisModel.organization_id == organization_id)
            .where(SavedThesisModel.visibility == "organization")
        )
    )
    db.execute(delete(ResearchReportComparisonModel).where(ResearchReportComparisonModel.organization_id == organization_id))
    _delete_thesis_research_rows(db, thesis_ids)


def export_research_intelligence(db: Session, owner_user_id: str) -> dict[str, list[dict]]:
    thesis_ids = _private_thesis_ids_for_account(db, owner_user_id)
    revisions = db.scalars(select(ThesisRevisionModel).where(ThesisRevisionModel.thesis_id.in_(thesis_ids))).all() if thesis_ids else []
    assumptions = db.scalars(select(ThesisAssumptionModel).where(ThesisAssumptionModel.thesis_id.in_(thesis_ids))).all() if thesis_ids else []
    catalysts = db.scalars(select(ThesisCatalystModel).where(ThesisCatalystModel.thesis_id.in_(thesis_ids))).all() if thesis_ids else []
    comparisons = db.scalars(
        select(ResearchReportComparisonModel)
        .where(ResearchReportComparisonModel.owner_user_id == owner_user_id)
        .where(ResearchReportComparisonModel.scope_class == "private")
        .where(ResearchReportComparisonModel.scope_key == f"private:{owner_user_id}")
        .where(ResearchReportComparisonModel.organization_id.is_(None))
    ).all()
    return {
        "thesis_revisions": [{"thesis_id": row.thesis_id, "revision_number": row.revision_number, "status": row.status, "created_at": row.created_at} for row in revisions],
        "research_assumptions": [{"id": row.assumption_id, "thesis_id": row.thesis_id, "revision_number": row.revision_number, "state": row.state, "statement": row.statement, "evidence_references": row.evidence_references} for row in assumptions],
        "research_catalysts": [{"id": row.id, "thesis_id": row.thesis_id, "title": row.title, "status": row.status, "date_precision": row.date_precision, "expected_date": row.expected_date, "window_start": row.window_start, "window_end": row.window_end} for row in catalysts],
        "report_comparisons": [{"id": row.id, "left_report_id": row.left_report_id, "right_report_id": row.right_report_id, "schema_version": row.schema_version, "created_at": row.created_at} for row in comparisons],
    }


def _private_thesis_ids_for_account(db: Session, owner_user_id: str) -> list[str]:
    """Personal lifecycle paths must never infer organization authority from creator history."""

    return list(
        db.scalars(
            select(SavedThesisModel.id)
            .where(SavedThesisModel.owner_user_id == owner_user_id)
            .where(SavedThesisModel.visibility == "private")
            .where(SavedThesisModel.organization_id.is_(None))
        )
    )


def _delete_thesis_research_rows(db: Session, thesis_ids: list[str]) -> None:
    if not thesis_ids:
        return
    db.execute(delete(ThesisAssumptionHeadModel).where(ThesisAssumptionHeadModel.thesis_id.in_(thesis_ids)))
    db.execute(delete(ThesisAssumptionModel).where(ThesisAssumptionModel.thesis_id.in_(thesis_ids)))
    db.execute(delete(ThesisCatalystModel).where(ThesisCatalystModel.thesis_id.in_(thesis_ids)))
    db.execute(delete(ThesisRevisionModel).where(ThesisRevisionModel.thesis_id.in_(thesis_ids)))


def _append_revision(
    db: Session,
    thesis: SavedThesisModel,
    *,
    actor_user_id: str | None,
    status: str,
    origin: str,
    change_reason: str | None,
) -> ThesisRevisionModel:
    number = (db.scalar(select(func.max(ThesisRevisionModel.revision_number)).where(ThesisRevisionModel.thesis_id == thesis.id)) or 0) + 1
    current_assumption_versions = [
        {
            "assumption_id": row.assumption_id,
            "assumption_record_id": row.current_record_id,
            "assumption_revision_number": row.current_revision_number,
        }
        for row in db.execute(
            select(
                ThesisAssumptionHeadModel.assumption_id,
                ThesisAssumptionHeadModel.current_record_id,
                ThesisAssumptionHeadModel.current_revision_number,
            )
            .where(ThesisAssumptionHeadModel.thesis_id == thesis.id)
            .order_by(ThesisAssumptionHeadModel.assumption_id)
        )
    ]
    record = ThesisRevisionModel(
        id=f"thr_{uuid4().hex[:12]}",
        thesis_id=thesis.id,
        revision_number=number,
        owner_user_id=thesis.owner_user_id,
        organization_id=thesis.organization_id if thesis.visibility == "organization" else None,
        title=thesis.title,
        strategy_text=thesis.strategy_text,
        protocols=list(thesis.protocols),
        assumptions_snapshot=dict(thesis.assumptions_json),
        explicit_assumption_ids=[item["assumption_id"] for item in current_assumption_versions],
        explicit_assumption_versions=current_assumption_versions,
        status=status,
        actor_user_id=actor_user_id,
        origin=origin,
        change_reason=change_reason,
        created_at=datetime.now(UTC),
    )
    db.add(record)
    db.flush()
    return record


def _locked_authorized_thesis(db: Session, actor: UserContext, thesis_id: str) -> SavedThesisModel:
    thesis = db.execute(
        select(SavedThesisModel).where(SavedThesisModel.id == thesis_id).with_for_update()
    ).scalars().one_or_none()
    if thesis is None or not can_update_saved_thesis(db, actor, thesis):
        raise HTTPException(status_code=404, detail="Thesis not found")
    return thesis


def _locked_authorized_read_thesis(db: Session, actor: UserContext, thesis_id: str) -> SavedThesisModel:
    thesis = db.execute(
        select(SavedThesisModel).where(SavedThesisModel.id == thesis_id).with_for_update()
    ).scalars().one_or_none()
    if thesis is None or not can_read_saved_thesis(db, actor, thesis):
        raise HTTPException(status_code=404, detail="Thesis not found")
    return thesis


def _authorized_thesis(db: Session, actor: UserContext, thesis_id: str, *, write: bool) -> SavedThesisModel:
    thesis = db.get(SavedThesisModel, thesis_id)
    allowed = can_update_saved_thesis(db, actor, thesis) if thesis is not None and write else can_read_saved_thesis(db, actor, thesis) if thesis is not None else False
    if thesis is None or not allowed:
        raise HTTPException(status_code=404, detail="Thesis not found")
    return thesis


def _authorized_report(db: Session, actor: UserContext, report_id: str) -> ReportModel:
    report = db.get(ReportModel, report_id)
    if report is None or not can_read_resource(actor, report, db) or not _active_organization_scope(db, actor, report, READ_ORG_ROLES):
        raise HTTPException(status_code=404, detail="Report not found")
    return report


def _authorized_evidence_report(
    db: Session,
    actor: UserContext,
    thesis: SavedThesisModel,
    report_id: str,
) -> ReportModel:
    report = _authorized_report(db, actor, report_id)
    if not _evidence_scope_matches_thesis(thesis, report):
        # The destination thesis is authoritative. Do not disclose whether an
        # otherwise-readable report belongs to another private or org scope.
        raise HTTPException(status_code=404, detail="Report not found")
    return report


def _evidence_scope_matches_thesis(thesis: SavedThesisModel, report: ReportModel) -> bool:
    if thesis.visibility == "private":
        return report.visibility == "private" and bool(thesis.owner_user_id) and report.owner_user_id == thesis.owner_user_id
    if thesis.visibility == "organization":
        return (
            report.visibility == "organization"
            and bool(thesis.organization_id)
            and report.organization_id == thesis.organization_id
        )
    return False


def _active_organization_scope(db: Session, actor: UserContext, resource, roles: set[str]) -> bool:
    """Never let ownership of a derived record bypass active organization scope."""

    if resource.visibility != "organization":
        return True
    return bool(resource.organization_id and has_org_role(db, actor.id, resource.organization_id, roles))


def _compatible_report_scope(left: ReportModel, right: ReportModel) -> tuple[str, str, str | None, str | None]:
    if left.visibility == "organization" or right.visibility == "organization":
        if left.visibility != "organization" or right.visibility != "organization" or not left.organization_id or left.organization_id != right.organization_id:
            raise HTTPException(status_code=404, detail="Reports are not in a compatible research scope")
        return "organization", f"organization:{left.organization_id}", None, left.organization_id
    if left.visibility != "private" or right.visibility != "private" or not left.owner_user_id or left.owner_user_id != right.owner_user_id:
        raise HTTPException(status_code=404, detail="Reports are not in a compatible research scope")
    return "private", f"private:{left.owner_user_id}", left.owner_user_id, None


def _resolve_evidence_references(
    db: Session,
    actor: UserContext,
    thesis: SavedThesisModel,
    references: list,
) -> list[dict]:
    resolved: list[dict] = []
    for reference in references:
        if reference.report_id is not None:
            report = _authorized_evidence_report(db, actor, thesis, reference.report_id)
            report_payload = ReportResponse.model_validate(report.report_json)
            by_id = {
                source.citation_lineage.citation_id: source.citation_lineage
                for source in report_payload.sources
                if source.citation_lineage is not None
            }
            if not reference.citation_ids:
                raise HTTPException(status_code=422, detail="Report-backed evidence requires citation_ids")
            for citation_id in reference.citation_ids:
                lineage = by_id.get(citation_id)
                if lineage is None:
                    raise HTTPException(status_code=422, detail="Citation is not authoritative for the supplied report")
                resolved.append({"classification": "authoritative_lineage", "report_id": report.id, "citation_lineage": lineage.model_dump(mode="json")})
        if reference.unverified_reference is not None:
            resolved.append({"classification": "unverified_external", "label": reference.unverified_reference})
    return resolved


def _revision_response(record: ThesisRevisionModel) -> ThesisRevisionResponse:
    return ThesisRevisionResponse(
        id=record.id,
        thesis_id=record.thesis_id,
        revision_number=record.revision_number,
        title=record.title,
        strategy_text=record.strategy_text,
        protocols=list(record.protocols),
        assumptions_snapshot=dict(record.assumptions_snapshot),
        explicit_assumption_ids=list(record.explicit_assumption_ids),
        explicit_assumption_versions=list(record.explicit_assumption_versions),
        status=record.status,
        actor_user_id=record.actor_user_id,
        origin=record.origin,
        change_reason=record.change_reason,
        created_at=record.created_at,
    )


def _assumption_response(record: ThesisAssumptionModel) -> ResearchAssumptionResponse:
    return ResearchAssumptionResponse(
        id=record.assumption_id,
        thesis_id=record.thesis_id,
        revision_number=record.revision_number,
        statement=record.statement,
        state=record.state,
        evidence_references=list(record.evidence_references),
        supersedes_record_id=record.supersedes_record_id,
        actor_user_id=record.actor_user_id,
        created_at=record.created_at,
    )


def _catalyst_response(record: ThesisCatalystModel) -> CatalystResponse:
    return CatalystResponse(
        id=record.id,
        thesis_id=record.thesis_id,
        title=record.title,
        description=record.description,
        expected_date=record.expected_date,
        window_start=record.window_start,
        window_end=record.window_end,
        date_precision=record.date_precision,
        status=record.status,
        uncertainty=record.uncertainty,
        evidence_references=list(record.evidence_references),
        revision_number=record.revision_number,
        actor_user_id=record.actor_user_id,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def _deterministic_report_diff(db: Session, left: ReportModel, right: ReportModel) -> dict:
    left_payload = ReportResponse.model_validate(left.report_json)
    right_payload = ReportResponse.model_validate(right.report_json)
    left_sections = {item.title: item.content for item in left_payload.sections}
    right_sections = {item.title: item.content for item in right_payload.sections}
    left_provenance = _report_synthesis_provenance(db, left.id)
    right_provenance = _report_synthesis_provenance(db, right.id)
    return {
        "strategy": _with_content_origin(
            _categorical_diff(left_payload.strategy_description, right_payload.strategy_description), "deterministic", "deterministic"
        ),
        "protocols": _with_content_origin(_set_diff(left_payload.protocols, right_payload.protocols), "deterministic", "deterministic"),
        "risk_rating": _with_content_origin(_categorical_diff(left_payload.risk_rating, right_payload.risk_rating), "deterministic", "deterministic"),
        "assumptions": _with_content_origin(_set_diff(left_payload.assumptions, right_payload.assumptions), "deterministic", "deterministic"),
        "missing_data": _with_content_origin(_set_diff(left_payload.missing_data, right_payload.missing_data), "deterministic", "deterministic"),
        "sections": {
            key: _with_content_origin(
                _categorical_diff(left_sections.get(key), right_sections.get(key)),
                _section_content_origin(key, left_provenance),
                _section_content_origin(key, right_provenance),
            )
            for key in sorted(set(left_sections) | set(right_sections))
        },
        "sources": _with_content_origin(_set_diff(_source_keys(left_payload.sources), _source_keys(right_payload.sources)), "deterministic", "deterministic"),
        "citation_lineage": _with_content_origin(_citation_diff(left_payload.sources, right_payload.sources), "deterministic", "deterministic"),
        "timestamps": _with_content_origin(_categorical_diff(left.created_at.isoformat(), right.created_at.isoformat()), "deterministic", "deterministic"),
        "comparison_provenance": {
            "computation_origin": "deterministic",
            "left_synthesis_outcome": left_provenance.outcome if left_provenance is not None else "unknown",
            "right_synthesis_outcome": right_provenance.outcome if right_provenance is not None else "unknown",
            "content_origin_rule": "Deterministic fields are code-owned; synthesizable sections use durable report-synthesis provenance and remain unknown without it.",
        },
    }


def _report_synthesis_provenance(db: Session, report_id: str) -> ModelRunProvenanceModel | None:
    rows = db.execute(
        select(ModelRunProvenanceModel)
        .where(ModelRunProvenanceModel.report_id == report_id)
        .where(ModelRunProvenanceModel.task_key == "report_synthesis")
        .order_by(ModelRunProvenanceModel.created_at.desc(), ModelRunProvenanceModel.id.desc())
    ).scalars().all()
    # A report should have one synthesis record. Ambiguous historical rows must
    # not be guessed into a content-origin classification.
    return rows[0] if len(rows) == 1 else None


def _section_content_origin(title: str, provenance: ModelRunProvenanceModel | None) -> str:
    if title not in SYNTHESIZABLE_SECTION_TITLES:
        return "deterministic"
    if provenance is None:
        return "unknown"
    if provenance.outcome == "succeeded" and provenance.validation_result == "accepted":
        return "model_assisted"
    if provenance.outcome in {"disabled", "provider_unavailable", "validation_fallback", "provider_failure"}:
        return "deterministic_fallback"
    return "unknown"


def _with_content_origin(change: dict, left_origin: str, right_origin: str) -> dict:
    return {**change, "left_content_origin": left_origin, "right_content_origin": right_origin}


def _categorical_diff(left: object, right: object) -> dict:
    if left is None and right is None:
        status = "unknown"
    elif left is None:
        status = "added"
    elif right is None:
        status = "removed"
    elif left == right:
        status = "unchanged"
    else:
        status = "changed"
    return {"status": status}


def _set_diff(left: list[str], right: list[str]) -> dict:
    left_set, right_set = set(left), set(right)
    return {
        "unchanged": sorted(left_set & right_set),
        "added": sorted(right_set - left_set),
        "removed": sorted(left_set - right_set),
    }


def _source_keys(sources: list[SourceReference]) -> list[str]:
    return sorted(
        source.citation_lineage.citation_id if source.citation_lineage else f"unverified:{source.title}:{source.source_type}"
        for source in sources
    )


def _citation_diff(left: list[SourceReference], right: list[SourceReference]) -> dict:
    def lineages(items: list[SourceReference]) -> dict[str, tuple[str, str]]:
        return {
            source.citation_lineage.citation_id: (
                source.citation_lineage.document_version_id,
                source.citation_lineage.document_version_checksum,
            )
            for source in items
            if source.citation_lineage is not None
        }
    left_items, right_items = lineages(left), lineages(right)
    return {
        "unchanged": sorted(key for key in left_items.keys() & right_items.keys() if left_items[key] == right_items[key]),
        "changed": sorted(key for key in left_items.keys() & right_items.keys() if left_items[key] != right_items[key]),
        "added": sorted(right_items.keys() - left_items.keys()),
        "removed": sorted(left_items.keys() - right_items.keys()),
    }


def _staleness_item(db: Session, index: int, source: SourceReference) -> dict:
    lineage = source.citation_lineage
    if lineage is None:
        return {"source_index": index, "status": "unknown", "classification": "unverified_or_non_lineage", "newer_version_exists": False, "detail": "The report source has no durable citation lineage."}
    source_row = db.get(KnowledgeSourceModel, lineage.source_id)
    document = db.get(KnowledgeDocumentModel, lineage.document_id)
    version = db.get(KnowledgeDocumentVersionModel, lineage.document_version_id)
    chunk = db.get(KnowledgeChunkModel, lineage.chunk_id)
    if source_row is None or document is None or version is None or chunk is None:
        return {"source_index": index, "citation_id": lineage.citation_id, "status": "unavailable", "newer_version_exists": False, "detail": "The recorded lineage cannot be fully resolved."}
    if source_row.deleted_at is not None or document.deleted_at is not None or version.deleted_at is not None or chunk.deleted_at is not None or source_row.status == "deleted" or document.status == "deleted" or version.status == "deleted":
        return {"source_index": index, "citation_id": lineage.citation_id, "status": "deleted", "newer_version_exists": False, "detail": "The recorded source lineage was deleted; the historical report is unchanged."}
    if version.checksum != lineage.document_version_checksum or chunk.content_checksum != lineage.chunk_checksum:
        return {"source_index": index, "citation_id": lineage.citation_id, "status": "unavailable", "newer_version_exists": False, "detail": "The durable identifiers no longer match the recorded checksums."}
    if document.current_version_id and document.current_version_id != version.id:
        return {"source_index": index, "citation_id": lineage.citation_id, "status": "superseded", "newer_version_exists": True, "detail": "A newer document version exists; this does not by itself make the historical claim false."}
    return {"source_index": index, "citation_id": lineage.citation_id, "status": "current", "newer_version_exists": False, "detail": "The recorded durable citation lineage remains current."}


def _comparison_response(record: ResearchReportComparisonModel) -> ReportComparisonResponse:
    return ReportComparisonResponse(
        id=record.id,
        left_report_id=record.left_report_id,
        right_report_id=record.right_report_id,
        created_at=record.created_at,
        schema_version=record.schema_version,
        changes=dict(record.comparison_json),
        uncertainty=["The comparison classifies deterministic report fields and citation lineage; it does not infer new market facts."],
    )


def _report_checksum(report: ReportModel) -> str:
    return _checksum(report.report_json)


def _checksum(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def _safe_research_question(value: str) -> bool:
    lowered = value.lower()
    return not any(token in lowered for token in (" buy", " sell", "allocate", "position size", "order", "wallet", "trade"))
