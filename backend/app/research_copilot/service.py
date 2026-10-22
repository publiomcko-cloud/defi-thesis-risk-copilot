from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from hashlib import sha256
from time import monotonic
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.agents.orchestrator import ResearchWorkflowTimeout, run_analysis_workflow
from app.auth.schemas import UserContext
from app.core.config import get_settings
from app.llm.base import SynthesisBudget
from app.llm.governance import record_model_run_provenance, record_model_run_quality_evidence
from app.models.analysis_request import AnalysisRequestModel
from app.models.report import ReportModel
from app.models.research_intelligence import ThesisAssumptionHeadModel, ThesisAssumptionModel
from app.models.saved_thesis import SavedThesisModel
from app.product_analytics.service import emit_product_event_safely
from app.quotas.service import ACTION_ANALYSIS, consume_quota
from app.reports.markdown_export import render_markdown_report
from app.schemas.analysis import AnalysisRequest, ManualInputs
from app.schemas.reports import ReportResponse
from app.schemas.research import (
    ResearchQuestionRequest,
    ResearchRunLimits,
    ResearchRunMetadata,
    ResearchRunSummary,
    ResearchRunsResponse,
    ResearchSourceObservation,
)
from app.services.report_service import save_report
from app.theses.policies import can_read_saved_thesis


_RUN_KEY_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{8,128}$")
_SUPPORTED_PROTOCOLS = frozenset({"aave", "morpho", "pendle"})


def start_thesis_research(
    db: Session,
    actor: UserContext,
    thesis_id: str,
    request: ResearchQuestionRequest,
    idempotency_key: str | None,
) -> ResearchRunSummary:
    settings = get_settings()
    thesis = _authorized_private_thesis(db, actor, thesis_id)
    if not idempotency_key or not _RUN_KEY_PATTERN.fullmatch(idempotency_key):
        raise HTTPException(status_code=422, detail="A valid Idempotency-Key is required for research runs.")
    protocols = sorted({str(item).strip().lower() for item in (thesis.protocols or []) if str(item).strip()})
    strategy_text = str(thesis.strategy_text)
    stable_thesis_id = thesis.id
    thesis_assumptions = _thesis_assumptions_snapshot(db, thesis)
    if len(protocols) > 3 or not set(protocols).issubset(_SUPPORTED_PROTOCOLS):
        raise HTTPException(
            status_code=422,
            detail="Synchronous research currently supports up to three tagged protocols: Aave, Morpho, and Pendle.",
        )

    input_checksum = _research_input_checksum(thesis, request, thesis_assumptions)
    existing = _existing_run(db, actor.id, idempotency_key)
    if existing is not None:
        return _existing_run_response(db, existing, thesis_id, input_checksum)

    started_at = datetime.now(UTC)
    execution_started = monotonic()
    deadline = execution_started + settings.research_run_wall_time_seconds
    run_id = f"analysis_{uuid4().hex[:16]}"
    report_id = f"report_{uuid4().hex[:16]}"
    run = AnalysisRequestModel(
        id=run_id,
        strategy_description=strategy_text,
        protocols=protocols,
        market_url=None,
        manual_inputs_json={},
        analysis_depth="deep",
        thesis_id=stable_thesis_id,
        research_question=request.question.strip(),
        research_run_key=idempotency_key,
        research_input_checksum=input_checksum,
        research_status="running",
        research_metadata_json=None,
        owner_user_id=actor.id,
        organization_id=None,
        visibility="private",
        anonymous_session_id=None,
        created_at=started_at,
    )
    db.add(run)
    try:
        # consume_quota commits the run reservation and quota increment together.
        consume_quota(db, actor, ACTION_ANALYSIS)
        db.commit()
    except IntegrityError:
        db.rollback()
        winner = _existing_run(db, actor.id, idempotency_key)
        if winner is None:
            raise HTTPException(status_code=409, detail="The research run could not be reserved safely.") from None
        return _existing_run_response(db, winner, thesis_id, input_checksum)
    except HTTPException:
        db.rollback()
        raise

    synthesis_budget = SynthesisBudget(
        total_tokens=settings.research_run_token_budget,
        max_output_tokens=min(1_000, max(256, settings.research_run_token_budget // 4)),
        cost_ceiling_microusd=settings.research_run_cost_ceiling_microusd,
        deadline_monotonic=deadline,
    )
    try:
        workflow = run_analysis_workflow(
            AnalysisRequest(
                strategy_description=strategy_text,
                protocols=protocols,
                market_url=None,
                manual_inputs=ManualInputs(),
                analysis_depth="deep",
            ),
            report_id,
            db,
            actor=actor,
            research_question=request.question.strip(),
            research_max_passes=settings.research_run_max_passes,
            source_document_budget=settings.research_run_max_documents,
            max_tool_invocations=settings.research_run_max_tool_invocations,
            max_model_calls=settings.research_run_max_model_calls,
            deadline_monotonic=deadline,
            synthesis_budget=synthesis_budget,
            thesis_assumptions=thesis_assumptions,
        )
        completed_at = datetime.now(UTC)
        evidence_gaps = list(dict.fromkeys(workflow.missing_data))
        source_observations = _source_observations(workflow, completed_at)
        model_run = workflow.model_run
        metadata = ResearchRunMetadata(
            run_id=run.id,
            thesis_id=stable_thesis_id,
            question=request.question.strip(),
            status="completed_with_gaps" if evidence_gaps else "completed",
            started_at=started_at,
            completed_at=completed_at,
            elapsed_ms=min(max(int((monotonic() - execution_started) * 1000), 0), 120_000),
            pass_count=workflow.pass_count,
            model_call_count=workflow.model_call_count,
            tool_invocation_count=workflow.tool_invocation_count,
            source_document_count=len(workflow.retrieved_context),
            limits=_limits(settings),
            tools=workflow.tool_trace or [],
            sources=source_observations,
            evidence_gaps=evidence_gaps,
            llm_used=workflow.model_run.outcome == "succeeded" and workflow.model_call_count > 0,
            llm_outcome=workflow.model_run.outcome,
            llm_fallback_reason=workflow.model_run.fallback_reason,
            model_provider=model_run.provider.provider_key if model_run.provider else None,
            model_key=model_run.provider.model_key if model_run.provider else None,
            route_version_id=model_run.route_version_id,
            evaluation_run_id=model_run.evaluation_run_id,
            prompt_checksum=model_run.prompt_checksum,
            input_tokens=model_run.input_tokens,
            output_tokens=model_run.output_tokens,
            total_tokens=model_run.total_tokens,
            cost_microusd=model_run.cost_microusd,
        )
        report = workflow.report.model_copy(update={"research": metadata})
        run.research_status = "completed"
        run.research_completed_at = completed_at
        run.research_metadata_json = metadata.model_dump(mode="json")
        save_report(
            report=report,
            analysis_request_id=run.id,
            report_markdown=render_markdown_report(report),
            db=db,
            owner_user_id=actor.id,
            visibility="private",
        )
        provenance = record_model_run_provenance(
            db,
            report_id=report.report_id,
            candidate=workflow.model_run,
            owner_user_id=actor.id,
            organization_id=None,
            anonymous_session_id=None,
        )
        record_model_run_quality_evidence(
            db,
            model_run=provenance,
            quality=workflow.model_quality,
        )
        if actor.auth_enabled and actor.anonymous_session_id is None:
            from app.entitlements.service import emit_usage

            emit_usage(
                db,
                owner_user_id=actor.id,
                unit_key="usage.analysis.completed.v1",
                source_type="report",
                source_id=report.report_id,
            )
        db.commit()
        emit_product_event_safely(
            db,
            owner_user_id=actor.id,
            event_name="analysis_completed",
            metadata={
                "actor_class": "authenticated",
                "execution_mode": "synchronous_research",
                "result_class": "report_created",
                "llm_used": metadata.llm_used,
            },
            source_boundary=report.report_id,
        )
        return _run_response(db, run, stable_thesis_id)
    except ResearchWorkflowTimeout:
        _mark_failed(db, run.id, "request_timeout", started_at)
        raise HTTPException(
            status_code=504,
            detail="The bounded research request exceeded its configured time budget; no report was saved.",
        ) from None
    except HTTPException:
        _mark_failed(db, run.id, "research_execution_rejected", started_at)
        raise
    except Exception:
        _mark_failed(db, run.id, "research_execution_failed", started_at)
        raise HTTPException(status_code=503, detail="Research could not be completed safely.") from None


def list_thesis_research_runs(db: Session, actor: UserContext, thesis_id: str) -> ResearchRunsResponse:
    _authorized_private_thesis(db, actor, thesis_id)
    runs = db.execute(
        select(AnalysisRequestModel)
        .where(AnalysisRequestModel.thesis_id == thesis_id)
        .where(AnalysisRequestModel.owner_user_id == actor.id)
        .where(AnalysisRequestModel.research_run_key.is_not(None))
        .order_by(AnalysisRequestModel.created_at.desc())
        .limit(50)
    ).scalars().all()
    return ResearchRunsResponse(items=[_run_response(db, run, thesis_id) for run in runs])


def get_thesis_research_run(
    db: Session,
    actor: UserContext,
    thesis_id: str,
    run_id: str,
) -> ResearchRunSummary:
    _authorized_private_thesis(db, actor, thesis_id)
    run = db.execute(
        select(AnalysisRequestModel)
        .where(AnalysisRequestModel.id == run_id)
        .where(AnalysisRequestModel.thesis_id == thesis_id)
        .where(AnalysisRequestModel.owner_user_id == actor.id)
        .where(AnalysisRequestModel.research_run_key.is_not(None))
    ).scalars().one_or_none()
    if run is None:
        raise HTTPException(status_code=404, detail="Research run not found")
    return _run_response(db, run, thesis_id)


def _authorized_private_thesis(db: Session, actor: UserContext, thesis_id: str) -> SavedThesisModel:
    thesis = db.execute(
        select(SavedThesisModel).where(SavedThesisModel.id == thesis_id).with_for_update()
    ).scalars().one_or_none()
    if (
        thesis is None
        or not can_read_saved_thesis(db, actor, thesis)
        or thesis.visibility != "private"
        or thesis.owner_user_id != actor.id
    ):
        raise HTTPException(status_code=404, detail="Thesis not found")
    return thesis


def _research_input_checksum(
    thesis: SavedThesisModel,
    request: ResearchQuestionRequest,
    thesis_assumptions: list[str],
) -> str:
    payload = {
        "thesis_id": thesis.id,
        "strategy_text": thesis.strategy_text,
        "protocols": sorted({str(item).lower() for item in (thesis.protocols or [])}),
        "thesis_assumptions": thesis_assumptions,
        "question": request.question.strip(),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    return sha256(encoded).hexdigest()


def _thesis_assumptions_snapshot(db: Session, thesis: SavedThesisModel) -> list[str]:
    """Return a bounded, deterministic snapshot of saved owner assumptions."""

    max_items_per_source = 16
    max_value_length = 600
    assumptions: list[str] = []
    legacy = thesis.assumptions_json if isinstance(thesis.assumptions_json, dict) else {}
    legacy_items = sorted(legacy.items(), key=lambda item: str(item[0]))
    for key, value in legacy_items[:max_items_per_source]:
        serialized = json.dumps(value, sort_keys=True, ensure_ascii=False, default=str)
        if len(serialized) > max_value_length:
            serialized = f'{serialized[:max_value_length - 17]}… [truncated]'
        assumptions.append(
            f"Legacy saved assumption {json.dumps(str(key)[:120], ensure_ascii=False)}: {serialized}"
        )
    if len(legacy_items) > max_items_per_source:
        assumptions.append(
            f"{len(legacy_items) - max_items_per_source} additional legacy assumption(s) omitted by the snapshot limit."
        )

    explicit_items = db.execute(
        select(ThesisAssumptionModel)
        .join(
            ThesisAssumptionHeadModel,
            ThesisAssumptionHeadModel.current_record_id == ThesisAssumptionModel.id,
        )
        .where(ThesisAssumptionHeadModel.thesis_id == thesis.id)
        .order_by(ThesisAssumptionHeadModel.assumption_id)
        .limit(max_items_per_source + 1)
    ).scalars().all()
    for item in explicit_items[:max_items_per_source]:
        statement = item.statement.strip()
        if len(statement) > max_value_length:
            statement = f"{statement[:max_value_length - 17]}… [truncated]"
        assumptions.append(
            f"Current explicit assumption {item.assumption_id} (revision {item.revision_number}, "
            f"state {item.state}): {json.dumps(statement, ensure_ascii=False)}"
        )
    if len(explicit_items) > max_items_per_source:
        assumptions.append("Additional current explicit assumptions omitted by the snapshot limit.")
    if not assumptions:
        assumptions.append("No saved thesis assumptions were recorded at run start.")
    return assumptions


def _existing_run(db: Session, owner_user_id: str, idempotency_key: str) -> AnalysisRequestModel | None:
    return db.execute(
        select(AnalysisRequestModel)
        .where(AnalysisRequestModel.owner_user_id == owner_user_id)
        .where(AnalysisRequestModel.research_run_key == idempotency_key)
    ).scalars().one_or_none()


def _existing_run_response(
    db: Session,
    run: AnalysisRequestModel,
    thesis_id: str,
    input_checksum: str,
) -> ResearchRunSummary:
    if run.thesis_id != thesis_id or run.research_input_checksum != input_checksum:
        raise HTTPException(status_code=409, detail="Idempotency-Key is already bound to different research input.")
    return _run_response(db, run, thesis_id)


def _run_response(db: Session, run: AnalysisRequestModel, thesis_id: str) -> ResearchRunSummary:
    report = db.execute(
        select(ReportModel).where(ReportModel.analysis_request_id == run.id)
    ).scalars().one_or_none()
    payload = run.research_metadata_json or {}
    metadata = None
    error_code = None
    if run.research_status == "completed" and payload:
        metadata = ResearchRunMetadata.model_validate(payload)
    elif isinstance(payload, dict):
        error_code = payload.get("error_code")
    return ResearchRunSummary(
        run_id=run.id,
        thesis_id=thesis_id,
        status=run.research_status or "failed",
        question=run.research_question or "",
        report_id=report.id if report else None,
        error_code=error_code,
        started_at=run.created_at,
        completed_at=run.research_completed_at,
        metadata=metadata,
    )


def _mark_failed(db: Session, run_id: str, error_code: str, started_at: datetime) -> None:
    db.rollback()
    run = db.get(AnalysisRequestModel, run_id)
    if run is None:
        return
    completed_at = datetime.now(UTC)
    run.research_status = "failed"
    run.research_completed_at = completed_at
    run.research_metadata_json = {
        "error_code": error_code,
        "started_at": started_at.isoformat(),
        "completed_at": completed_at.isoformat(),
        "limits": _limits(get_settings()).model_dump(mode="json"),
    }
    db.commit()


def _limits(settings) -> ResearchRunLimits:
    return ResearchRunLimits(
        max_passes=settings.research_run_max_passes,
        max_model_calls=settings.research_run_max_model_calls,
        max_tool_invocations=settings.research_run_max_tool_invocations,
        max_documents=settings.research_run_max_documents,
        token_budget=settings.research_run_token_budget,
        cost_ceiling_microusd=settings.research_run_cost_ceiling_microusd,
        wall_time_seconds=settings.research_run_wall_time_seconds,
    )


def _source_observations(workflow, completed_at: datetime) -> list[ResearchSourceObservation]:
    observations: list[ResearchSourceObservation] = []
    for result in workflow.retrieved_context:
        metadata = result.metadata
        lineage = metadata.get("citation_lineage") if isinstance(metadata.get("citation_lineage"), dict) else {}
        source_time = _parse_time(
            metadata.get("source_timestamp")
            or metadata.get("published_at")
            or metadata.get("updated_at")
            or metadata.get("last_updated")
        )
        title = str(metadata.get("document_title") or "Curated protocol source")
        section = str(metadata.get("section_title") or "")
        observations.append(
            ResearchSourceObservation(
                source_id=result.chunk_id,
                source_version_id=(
                    str(metadata.get("document_version_id") or lineage.get("document_version_id"))[:128]
                    if metadata.get("document_version_id") or lineage.get("document_version_id")
                    else None
                ),
                source_version_checksum=(
                    str(lineage.get("document_version_checksum"))[:128]
                    if lineage.get("document_version_checksum")
                    else None
                ),
                title=f"{title} — {section}".strip(" —")[:255],
                source_type="knowledge_base",
                url=str(metadata.get("source_url"))[:2_048] if metadata.get("source_url") else None,
                protocol=str(metadata.get("protocol"))[:64] if metadata.get("protocol") else None,
                status="retrieved",
                observed_at=completed_at,
                source_timestamp=source_time,
                freshness_note=(
                    "Curated source timestamp supplied by the source metadata."
                    if source_time
                    else "Retrieval time recorded; source publication time was not supplied."
                ),
            )
        )
    for adapter in workflow.market_data.data.get("adapters", []):
        source = str(adapter.get("source") or "market-data")
        status = str(adapter.get("status") or "unavailable")
        if status not in {"live", "cached", "manual", "manual_fallback", "unavailable"}:
            status = "unavailable"
        observed_at = _parse_time(adapter.get("observed_at")) or completed_at
        notes = {
            "live": "Adapter response capture time; upstream observation timestamp was not supplied.",
            "cached": "Cached result capture time; provider observation timestamp was not supplied.",
            "manual": "Manual adapter selected; any supplied values are owner-entered and not independently verified.",
            "manual_fallback": "Owner-supplied values captured for this run; not independently verified.",
            "unavailable": "Adapter attempt time; no market observation was available.",
        }
        observations.append(
            ResearchSourceObservation(
                source_id=f"market:{source}"[:128],
                title=f"{source} market data"[:255],
                source_type="market_data",
                status=status,
                observed_at=observed_at,
                freshness_note=notes[status],
            )
        )
    return observations[:32]


def _parse_time(value: object) -> datetime | None:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)
