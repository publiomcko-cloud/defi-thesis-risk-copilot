from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal, ROUND_UP
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.policies import READ_ORG_ROLES, WRITE_ORG_ROLES, has_org_role
from app.auth.schemas import UserContext
from app.auth.service import record_audit_event, user_context
from app.core.config import get_settings
from app.jobs.access import get_visible_job
from app.jobs.registry import validate_submission_schema
from app.jobs.schemas import (
    JobEventResponse,
    JobEventsResponse,
    JobInputEnvelope,
    JobOperationsResponse,
    JobResponse,
    JobSubmissionRequest,
)
from app.jobs.state import append_job_event, transition_job
from app.models.job import JobCapacityReservationModel, JobEventModel, JobModel, ProviderCostReservationModel
from app.models.organization import OrganizationModel
from app.models.usage_quota import UsageQuotaModel
from app.models.user import UserModel
from app.models.vast_session import VastSessionModel
from app.models.worker import WorkerModel
from app.quotas.service import ACTION_ANALYSIS, _day_window, _limit_for


PENDING_JOB_STATUSES = {"queued", "leased", "retry_wait", "cancel_requested"}
RUNNING_JOB_STATUSES = {"running"}
TERMINAL_REPLAYABLE_STATUSES = {"failed", "dead_letter"}
_RESERVED_INPUT_KEYS = {"_server_context", "owner_user_id", "created_by_user_id", "priority_class", "status"}
_SENSITIVE_KEY_PARTS = {
    "api_key",
    "apikey",
    "authorization",
    "credential",
    "cookie",
    "password",
    "private_key",
    "secret",
    "access_token",
    "refresh_token",
}


def ensure_jobs_enabled() -> None:
    if not get_settings().jobs_enabled:
        raise HTTPException(status_code=503, detail="Durable job submission is disabled.")


def submit_job(
    db: Session,
    actor: UserContext,
    request: JobSubmissionRequest,
    idempotency_key: str,
    *,
    replay_of_job_id: str | None = None,
    created_by_user_id: str | None = None,
    allow_provider_job: bool = False,
) -> tuple[JobModel, bool]:
    """Create one queued job and its reservation in a single database transaction.

    A unique idempotency constraint is the final concurrency boundary. A conflicting
    flush rolls back the whole tentative transaction, including its quota reservation,
    and then returns the already-authorized matching job.
    """

    ensure_jobs_enabled()
    if request.job_type == "vast.session.start" and not allow_provider_job:
        raise HTTPException(status_code=403, detail="Vast jobs require the dedicated administrator endpoint.")
    if len(idempotency_key.strip()) < 8 or len(idempotency_key) > 128:
        raise HTTPException(status_code=422, detail="Idempotency-Key must be between 8 and 128 characters.")
    _validate_submission_input(request.input_json)
    validate_submission_schema(request.job_type, request.input_schema_version, request.input_json)
    scope = _resolve_scope(db, actor, request.organization_id)
    fingerprint = _request_fingerprint(request, scope["organization_id"])

    for _ in range(3):
        existing = _idempotent_job(db, scope, request.job_type, idempotency_key)
        if existing is not None:
            if existing.request_fingerprint != fingerprint:
                raise HTTPException(status_code=409, detail="Idempotency conflict: the key was used with different input.")
            return existing, True
        try:
            job = _create_reserved_job(
                db,
                actor=actor,
                request=request,
                scope=scope,
                idempotency_key=idempotency_key,
                fingerprint=fingerprint,
                replay_of_job_id=replay_of_job_id,
                created_by_user_id=created_by_user_id or actor.id,
            )
            record_audit_event(
                db,
                created_by_user_id or actor.id,
                "job.replayed" if replay_of_job_id else "job.submitted",
                "job",
                job.id,
                {"job_type": job.job_type, "organization_id": job.organization_id, "replay_of_job_id": replay_of_job_id},
                commit=False,
            )
            db.commit()
            db.refresh(job)
            return job, False
        except IntegrityError:
            db.rollback()
            # A concurrent matching request may have created the job or quota row.
            existing = _idempotent_job(db, scope, request.job_type, idempotency_key)
            if existing is not None:
                if existing.request_fingerprint != fingerprint:
                    raise HTTPException(status_code=409, detail="Idempotency conflict: the key was used with different input.")
                return existing, True
    raise HTTPException(status_code=409, detail="Unable to reserve the job. Retry the request.")


def list_visible_jobs(db: Session, actor: UserContext, limit: int) -> list[JobModel]:
    organization_ids = select(OrganizationModel.id).where(
        OrganizationModel.status == "active",
        OrganizationModel.deleted_at.is_(None),
        OrganizationModel.id.in_(
            select_from_active_memberships(actor.id)
        ),
    )
    return db.execute(
        select(JobModel)
        .where(JobModel.deleted_at.is_(None))
        .where(
            or_(
                JobModel.owner_user_id == actor.id,
                (JobModel.visibility == "organization") & (JobModel.organization_id.in_(organization_ids)),
            )
        )
        .order_by(JobModel.created_at.desc(), JobModel.id.desc())
        .limit(limit)
    ).scalars().all()


def job_operations_summary(db: Session) -> JobOperationsResponse:
    """Return only aggregate operational state for the administrator surface."""

    def count(statement) -> int:
        return int(db.execute(statement).scalar_one() or 0)

    return JobOperationsResponse(
        queued_jobs=count(
            select(func.count())
            .select_from(JobModel)
            .where(JobModel.deleted_at.is_(None))
            .where(JobModel.status.in_({"queued", "retry_wait"}))
        ),
        leased_or_running_jobs=count(
            select(func.count())
            .select_from(JobModel)
            .where(JobModel.deleted_at.is_(None))
            .where(JobModel.status.in_({"leased", "running", "cancel_requested"}))
        ),
        dead_letter_jobs=count(
            select(func.count())
            .select_from(JobModel)
            .where(JobModel.deleted_at.is_(None))
            .where(JobModel.status == "dead_letter")
        ),
        active_workers=count(select(func.count()).select_from(WorkerModel).where(WorkerModel.status == "active")),
        stale_workers=count(select(func.count()).select_from(WorkerModel).where(WorkerModel.status == "stale")),
        provider_cleanup_failures=count(
            select(func.count()).select_from(VastSessionModel).where(VastSessionModel.status == "cleanup_failed")
        ),
    )


def select_from_active_memberships(user_id: str):
    from app.models.organization import OrganizationMembershipModel

    return select(OrganizationMembershipModel.organization_id).where(
        OrganizationMembershipModel.user_id == user_id,
        OrganizationMembershipModel.status == "active",
    )


def cancel_job(db: Session, actor: UserContext, job_id: str) -> JobModel:
    job = get_visible_job(db, actor, job_id)
    if not _can_mutate_job(db, actor, job):
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status in {"completed", "failed", "cancelled", "dead_letter"}:
        return job
    if job.status != "cancel_requested":
        transition_job(
            db,
            job,
            "cancel_requested",
            actor_user_id=actor.id,
            message="Cancellation requested by an authorized user.",
        )
    if job.status == "cancel_requested" and job.leased_by_worker_id is None:
        transition_job(
            db,
            job,
            "cancelled",
            actor_user_id=actor.id,
            message="Queued job cancelled before worker execution.",
        )
        _release_capacity(db, job)
    record_audit_event(db, actor.id, "job.cancel_requested", "job", job.id, {"status": job.status}, commit=False)
    db.commit()
    db.refresh(job)
    return job


def list_job_events(db: Session, actor: UserContext, job_id: str, after_sequence: int, limit: int) -> JobEventsResponse:
    get_visible_job(db, actor, job_id)
    events = db.execute(
        select(JobEventModel)
        .where(JobEventModel.job_id == job_id)
        .where(JobEventModel.sequence_number > after_sequence)
        .order_by(JobEventModel.sequence_number)
        .limit(limit + 1)
    ).scalars().all()
    page = events[:limit]
    return JobEventsResponse(
        items=[job_event_response(event) for event in page],
        next_after_sequence=page[-1].sequence_number if len(events) > limit and page else None,
    )


def replay_job(db: Session, operator: UserContext, job_id: str) -> JobModel:
    ensure_jobs_enabled()
    original = db.execute(
        select(JobModel).where(JobModel.id == job_id).where(JobModel.deleted_at.is_(None))
    ).scalars().one_or_none()
    if original is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if original.status not in TERMINAL_REPLAYABLE_STATUSES:
        raise HTTPException(status_code=409, detail="Only failed or dead-letter jobs can be replayed.")
    if not original.owner_user_id:
        raise HTTPException(status_code=409, detail="Replay requires an active job owner.")
    owner = db.get(UserModel, original.owner_user_id)
    if owner is None or not owner.is_active or owner.account_status != "active" or owner.deleted_at is not None:
        raise HTTPException(status_code=409, detail="Replay target is no longer active.")
    if original.organization_id and not has_org_role(db, owner.id, original.organization_id, WRITE_ORG_ROLES):
        raise HTTPException(status_code=409, detail="Replay organization scope is no longer active.")
    request_input = original.input_json.get("request") if isinstance(original.input_json, dict) else None
    if not isinstance(request_input, dict):
        raise HTTPException(status_code=409, detail="Job input is not replayable.")
    request = JobSubmissionRequest(
        job_type=original.job_type,
        input_schema_version=original.input_schema_version,
        input_json=request_input,
        organization_id=original.organization_id,
    )
    owner_actor = user_context(owner, auth_enabled=True)
    replay_key = f"replay_{original.id}_{uuid4().hex[:16]}"
    job, _ = submit_job(
        db,
        owner_actor,
        request,
        replay_key,
        replay_of_job_id=original.id,
        created_by_user_id=operator.id,
        allow_provider_job=original.job_type == "vast.session.start",
    )
    return job


def job_response(job: JobModel) -> JobResponse:
    return JobResponse(
        id=job.id,
        job_type=job.job_type,
        status=job.status,
        owner_user_id=job.owner_user_id,
        organization_id=job.organization_id,
        visibility=job.visibility,
        progress_percent=job.progress_percent,
        progress_message=job.progress_message,
        attempt_count=job.attempt_count,
        max_attempts=job.max_attempts,
        result_resource_type=job.result_resource_type,
        result_resource_id=job.result_resource_id,
        error_code=job.error_code,
        error_summary=job.error_summary,
        queue_expires_at=job.queue_expires_at,
        deadline_at=job.deadline_at,
        replay_of_job_id=job.replay_of_job_id,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


def submit_vast_start_job(
    db: Session,
    actor: UserContext,
    *,
    allow_remote_gpu: bool,
    warm_instance: bool,
    idempotency_key: str,
) -> tuple[JobModel, bool]:
    """Queue an administrator-approved server-profiled Vast startup request."""

    settings = get_settings()
    if not actor.is_admin:
        raise HTTPException(status_code=403, detail="Platform administrator role required")
    if not settings.vast_job_enabled or not settings.vast_enabled:
        raise HTTPException(status_code=503, detail="Vast job execution is disabled.")
    if not settings.vast_dry_run and (
        not settings.vast_real_rentals_enabled or settings.vast_reconciliation_profile != "verified_v1"
    ):
        raise HTTPException(status_code=503, detail="Real Vast.ai rentals are disabled until reconciliation is verified.")
    if not settings.vast_dry_run and not allow_remote_gpu:
        raise HTTPException(status_code=422, detail="Remote GPU use must be explicitly allowed.")
    return submit_job(
        db,
        actor,
        JobSubmissionRequest(
            job_type="vast.session.start",
            input_schema_version="vast.session.start.v1",
            input_json={
                "allow_remote_gpu": allow_remote_gpu,
                "warm_instance": warm_instance,
            },
        ),
        idempotency_key,
        allow_provider_job=True,
    )


def job_event_response(event: JobEventModel) -> JobEventResponse:
    return JobEventResponse(
        id=event.id,
        job_id=event.job_id,
        sequence_number=event.sequence_number,
        event_type=event.event_type,
        message=event.message,
        metadata_json=event.metadata_json,
        actor_user_id=event.actor_user_id,
        worker_id=event.worker_id,
        created_at=event.created_at,
    )


def _create_reserved_job(
    db: Session,
    *,
    actor: UserContext,
    request: JobSubmissionRequest,
    scope: dict[str, str | None],
    idempotency_key: str,
    fingerprint: str,
    replay_of_job_id: str | None,
    created_by_user_id: str,
) -> JobModel:
    _validate_enabled_job_type(request.job_type)
    estimated_cost_microusd = _estimated_job_cost_microusd(request.job_type)
    _reserve_capacity(db, actor, scope["organization_id"], request.job_type, estimated_cost_microusd)
    _reserve_quota(db, actor, request.job_type)
    now = datetime.now(UTC)
    result_resource_type, result_resource_id, extra_context = _preallocate_result_resource(request.job_type)
    queue_expires_at = now + timedelta(seconds=get_settings().job_max_queue_age_seconds)
    input_snapshot = {
        "request": request.input_json,
        "_server_context": {
            "owner_user_id": actor.id,
            "organization_id": scope["organization_id"],
            "visibility": "organization" if scope["organization_id"] else "private",
            "submitted_by_user_id": created_by_user_id,
            **extra_context,
        },
    }
    job = JobModel(
        id=f"job_{uuid4().hex[:12]}",
        job_type=request.job_type,
        status="queued",
        priority_class="admin" if actor.is_admin else "standard",
        owner_user_id=actor.id,
        organization_id=scope["organization_id"],
        created_by_user_id=created_by_user_id,
        visibility="organization" if scope["organization_id"] else "private",
        input_schema_version=request.input_schema_version,
        input_json=input_snapshot,
        request_fingerprint=fingerprint,
        result_resource_type=result_resource_type,
        result_resource_id=result_resource_id,
        max_attempts=get_settings().job_default_max_attempts,
        available_at=now,
        queue_expires_at=queue_expires_at,
        deadline_at=queue_expires_at,
        progress_percent=0,
        idempotency_subject_type=scope["subject_type"],
        idempotency_subject_id=scope["subject_id"],
        idempotency_key=idempotency_key,
        estimated_cost_microusd=estimated_cost_microusd,
        reserved_cost_microusd=estimated_cost_microusd,
        actual_cost_microusd=0,
        replay_of_job_id=replay_of_job_id,
        created_at=now,
        updated_at=now,
    )
    db.add(job)
    db.flush()
    _create_provider_cost_reservation(db, job, now)
    append_job_event(
        db,
        job,
        event_type="job.queued",
        message="Job accepted and queued for controlled worker execution.",
        actor_user_id=created_by_user_id,
        metadata={"result_resource_id": result_resource_id, "replay_of_job_id": replay_of_job_id},
    )
    return job


def _resolve_scope(db: Session, actor: UserContext, organization_id: str | None) -> dict[str, str | None]:
    if organization_id:
        if not has_org_role(db, actor.id, organization_id, WRITE_ORG_ROLES):
            raise HTTPException(status_code=404, detail="Organization not found")
        return {"organization_id": organization_id, "subject_type": "organization", "subject_id": organization_id}
    return {"organization_id": None, "subject_type": "user", "subject_id": actor.id}


def _request_fingerprint(request: JobInputEnvelope, organization_id: str | None) -> str:
    normalized = {
        "job_type": request.job_type,
        "input_schema_version": request.input_schema_version,
        "input_json": request.input_json,
        "organization_id": organization_id,
    }
    encoded = json.dumps(normalized, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _idempotent_job(db: Session, scope: dict[str, str | None], job_type: str, key: str) -> JobModel | None:
    return db.execute(
        select(JobModel)
        .where(JobModel.idempotency_subject_type == scope["subject_type"])
        .where(JobModel.idempotency_subject_id == scope["subject_id"])
        .where(JobModel.job_type == job_type)
        .where(JobModel.idempotency_key == key)
    ).scalars().one_or_none()


def _reserve_capacity(
    db: Session,
    actor: UserContext,
    organization_id: str | None,
    job_type: str,
    estimated_cost_microusd: int,
) -> None:
    """Serialize capacity checks through durable rows in a stable lock order."""

    settings = get_settings()
    scopes = _capacity_scopes(actor.id, organization_id, job_type)
    records: list[tuple[JobCapacityReservationModel, int, int, str]] = []
    for scope_type, scope_id, pending_limit, running_limit, label in scopes:
        record = _get_capacity_record(db, scope_type, scope_id)
        if pending_limit == 0:
            raise HTTPException(status_code=429, detail=f"Job {label} pending capacity is disabled.")
        if record.pending_count >= pending_limit:
            raise HTTPException(status_code=429, detail=f"Job {label} pending capacity exceeded.")
        if running_limit == 0:
            # Running slots are only consumed by the worker protocol in Phase 17C.
            # Rejecting at submission would incorrectly block bounded queued work.
            pass
        records.append((record, pending_limit, running_limit, label))
    for record, _, _, _ in records:
        record.pending_count += 1
        record.updated_at = datetime.now(UTC)
    _reserve_daily_cost(
        db,
        _get_capacity_record(db, "global", "all"),
        settings.job_daily_cost_budget_microusd,
        estimated_cost_microusd,
    )


def _release_capacity(db: Session, job: JobModel) -> None:
    for scope_type, scope_id, _, _, _ in _capacity_scopes(job.owner_user_id or "deleted", job.organization_id, job.job_type):
        record = db.execute(
            select(JobCapacityReservationModel)
            .where(JobCapacityReservationModel.scope_type == scope_type)
            .where(JobCapacityReservationModel.scope_id == scope_id)
            .with_for_update()
        ).scalars().one_or_none()
        if record is not None and record.pending_count > 0:
            record.pending_count -= 1
            record.updated_at = datetime.now(UTC)
    _release_unused_cost_reservation(db, job)


def move_pending_capacity_to_running(db: Session, job: JobModel) -> None:
    """Move an accepted job into a worker slot under the same scope locks."""

    records = _capacity_records(db, job)
    for record, _, running_limit, label in records:
        if running_limit == 0 or record.running_count >= running_limit:
            raise HTTPException(status_code=429, detail=f"Job {label} running capacity exceeded.")
    now = datetime.now(UTC)
    for record, _, _, _ in records:
        if record.pending_count <= 0:
            raise HTTPException(status_code=409, detail="Job capacity reservation is inconsistent.")
        record.pending_count -= 1
        record.running_count += 1
        record.updated_at = now


def move_running_capacity_to_pending(db: Session, job: JobModel) -> None:
    records = _capacity_records(db, job)
    now = datetime.now(UTC)
    for record, pending_limit, _, label in records:
        if record.running_count <= 0:
            raise HTTPException(status_code=409, detail="Job running reservation is inconsistent.")
        if record.pending_count >= pending_limit:
            raise HTTPException(status_code=429, detail=f"Job {label} pending capacity exceeded.")
    for record, _, _, _ in records:
        record.running_count -= 1
        record.pending_count += 1
        record.updated_at = now


def release_running_capacity(db: Session, job: JobModel) -> None:
    now = datetime.now(UTC)
    for record, _, _, _ in _capacity_records(db, job):
        if record.running_count > 0:
            record.running_count -= 1
            record.updated_at = now


def _release_unused_cost_reservation(db: Session, job: JobModel) -> None:
    """Return a reservation only when the provider work never completed.

    Completed provider jobs retain their reservation for the daily spend guard.  A queued
    cancellation, expiry, or pre-execution authorization failure must not consume that
    capacity for the rest of the day.
    """

    if job.reserved_cost_microusd <= 0:
        return
    record = _get_capacity_record(db, "global", "all")
    period_start, period_end = _day_window()
    if record.budget_period_start == period_start and record.budget_period_end == period_end:
        record.reserved_cost_microusd = max(0, record.reserved_cost_microusd - job.reserved_cost_microusd)
        record.updated_at = datetime.now(UTC)
    job.reserved_cost_microusd = 0
    reservation = db.execute(
        select(ProviderCostReservationModel)
        .where(ProviderCostReservationModel.job_id == job.id)
        .with_for_update()
    ).scalars().one_or_none()
    if reservation is not None and reservation.status not in {"completed", "released", "cancelled"}:
        reservation.status = "released"
        reservation.reserved_cost_microusd = 0
        reservation.released_at = datetime.now(UTC)
        reservation.updated_at = reservation.released_at


def _capacity_records(
    db: Session,
    job: JobModel,
) -> list[tuple[JobCapacityReservationModel, int, int, str]]:
    records: list[tuple[JobCapacityReservationModel, int, int, str]] = []
    for scope_type, scope_id, pending_limit, running_limit, label in _capacity_scopes(
        job.owner_user_id or "deleted", job.organization_id, job.job_type
    ):
        record = _get_capacity_record(db, scope_type, scope_id)
        records.append((record, pending_limit, running_limit, label))
    return records


def _capacity_scopes(
    owner_user_id: str,
    organization_id: str | None,
    job_type: str,
) -> list[tuple[str, str, int, int, str]]:
    settings = get_settings()
    scopes = [
        ("global", "all", settings.job_global_pending_limit, settings.job_global_running_limit, "global"),
        ("provider", f"controlled:{job_type}", settings.job_provider_pending_limit, settings.job_provider_running_limit, "provider"),
        ("user", owner_user_id, settings.job_user_pending_limit, settings.job_user_running_limit, "user"),
    ]
    if organization_id:
        scopes.append(
            ("organization", organization_id, settings.job_org_pending_limit, settings.job_org_running_limit, "organization")
        )
    return sorted(scopes, key=lambda item: (item[0], item[1]))


def _get_capacity_record(db: Session, scope_type: str, scope_id: str) -> JobCapacityReservationModel:
    record = db.execute(
        select(JobCapacityReservationModel)
        .where(JobCapacityReservationModel.scope_type == scope_type)
        .where(JobCapacityReservationModel.scope_id == scope_id)
        .with_for_update()
    ).scalars().one_or_none()
    if record is not None:
        return record
    now = datetime.now(UTC)
    record = JobCapacityReservationModel(
        id=f"jobcap_{uuid4().hex[:12]}",
        scope_type=scope_type,
        scope_id=scope_id,
        pending_count=0,
        running_count=0,
        reserved_cost_microusd=0,
        created_at=now,
        updated_at=now,
    )
    db.add(record)
    # The unique scope constraint deliberately raises on first-use contention. The
    # outer submission loop rolls back all tentative reservations and retries.
    db.flush()
    return record


def _reserve_daily_cost(
    db: Session,
    global_record: JobCapacityReservationModel,
    budget_microusd: int,
    estimated_cost_microusd: int,
) -> None:
    period_start, period_end = _day_window()
    if global_record.budget_period_start != period_start or global_record.budget_period_end != period_end:
        global_record.budget_period_start = period_start
        global_record.budget_period_end = period_end
        global_record.reserved_cost_microusd = 0
    if budget_microusd and global_record.reserved_cost_microusd + estimated_cost_microusd > budget_microusd:
        raise HTTPException(status_code=429, detail="Daily job cost budget exceeded.")
    global_record.reserved_cost_microusd += estimated_cost_microusd
    global_record.updated_at = datetime.now(UTC)


def _create_provider_cost_reservation(db: Session, job: JobModel, now: datetime) -> None:
    if job.job_type != "vast.session.start":
        return
    period_start, period_end = _day_window()
    db.add(
        ProviderCostReservationModel(
            id=f"jobcost_{job.id}",
            job_id=job.id,
            provider="vast_ai",
            period_start=period_start,
            period_end=period_end,
            reserved_cost_microusd=job.reserved_cost_microusd,
            actual_cost_microusd=0,
            status="reserved",
            created_at=now,
            updated_at=now,
        )
    )


def _reserve_quota(db: Session, actor: UserContext, job_type: str) -> None:
    if actor.is_admin and get_settings().quota_admin_exempt:
        return
    action = ACTION_ANALYSIS if job_type == "analysis.generate" else None
    if action is None:
        raise HTTPException(status_code=403, detail="This job type is not enabled.")
    limit = _limit_for(actor.plan, action)
    if limit is None:
        return
    period_start, period_end = _day_window()
    record = db.execute(
        select(UsageQuotaModel)
        .where(UsageQuotaModel.subject_type == "user")
        .where(UsageQuotaModel.subject_id == actor.id)
        .where(UsageQuotaModel.action == action)
        .where(UsageQuotaModel.period_start == period_start)
        .where(UsageQuotaModel.period_end == period_end)
        .with_for_update()
    ).scalars().one_or_none()
    now = datetime.now(UTC)
    if record is None:
        record = UsageQuotaModel(
            id=f"quota_{uuid4().hex[:12]}",
            subject_type="user",
            subject_id=actor.id,
            plan=actor.plan,
            action=action,
            period_start=period_start,
            period_end=period_end,
            used=0,
            limit=limit,
            created_at=now,
            updated_at=now,
        )
        db.add(record)
    if record.used >= record.limit:
        raise HTTPException(status_code=429, detail=f"Daily {action} quota exceeded.")
    record.used += 1
    record.updated_at = now


def _validate_enabled_job_type(job_type: str) -> None:
    if job_type == "analysis.generate":
        return
    if job_type == "vast.session.start" and get_settings().vast_job_enabled:
        return
    raise HTTPException(status_code=403, detail="This job type is not enabled.")


def _preallocate_result_resource(job_type: str) -> tuple[str, str, dict[str, str]]:
    if job_type == "analysis.generate":
        report_id = f"report_{uuid4().hex[:12]}"
        return "report", report_id, {
            "analysis_request_id": f"analysis_{uuid4().hex[:12]}",
            "report_id": report_id,
        }
    if job_type == "vast.session.start":
        session_id = f"vast_{uuid4().hex[:12]}"
        return "vast_session", session_id, {"vast_session_id": session_id}
    raise HTTPException(status_code=403, detail="This job type is not enabled.")


def _estimated_job_cost_microusd(job_type: str) -> int:
    if job_type != "vast.session.start":
        return 0
    settings = get_settings()
    estimated = (
        Decimal(str(settings.vast_max_hourly_cost_usd))
        * Decimal(settings.vast_max_session_minutes)
        / Decimal(60)
        * Decimal(1_000_000)
    )
    return int(estimated.to_integral_value(rounding=ROUND_UP))


def _validate_submission_input(value: dict) -> None:
    def visit(item, path: str = "input_json") -> None:
        if isinstance(item, dict):
            for key, nested in item.items():
                normalized = str(key).lower().replace("-", "_").replace(" ", "_")
                if normalized in _RESERVED_INPUT_KEYS or any(part in normalized for part in _SENSITIVE_KEY_PARTS):
                    raise HTTPException(status_code=422, detail=f"{path}.{key} is not allowed in a job payload.")
                visit(nested, f"{path}.{key}")
        elif isinstance(item, list):
            for index, nested in enumerate(item):
                visit(nested, f"{path}[{index}]")

    visit(value)


def _can_mutate_job(db: Session, actor: UserContext, job: JobModel) -> bool:
    return bool(
        job.owner_user_id == actor.id
        or (
            job.visibility == "organization"
            and job.organization_id
            and has_org_role(db, actor.id, job.organization_id, WRITE_ORG_ROLES)
        )
    )
