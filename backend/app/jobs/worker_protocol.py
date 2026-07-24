from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from secrets import token_urlsafe

from fastapi import HTTPException
from sqlalchemy import case, select
from sqlalchemy.orm import Session

from app.auth.security import constant_time_equal, hash_job_lease_token, redact_sensitive
from app.auth.service import user_context
from app.core.config import get_settings
from app.jobs.control_service import (
    _release_capacity,
    move_pending_capacity_to_running,
    move_running_capacity_to_pending,
    release_running_capacity,
)
from app.jobs.lifecycle import mark_job_artifacts_incomplete
from app.jobs.registry import validate_result_schema
from app.jobs.schemas import (
    JobResultEnvelope,
    WorkerCancellationResponse,
    WorkerClaimedJob,
    WorkerClaimResponse,
    WorkerFailureRequest,
    WorkerHeartbeatRequest,
    WorkerLeaseRequest,
    WorkerMutationResponse,
    WorkerProgressRequest,
)
from app.jobs.state import append_job_event, transition_job
from app.jobs.worker_service import verify_worker_credential
from app.models.job import JobAttemptModel, JobCapacityReservationModel, JobModel
from app.models.organization import OrganizationMembershipModel, OrganizationModel
from app.models.user import UserModel
from app.models.vast_session import VastSessionModel
from app.models.worker import WorkerCredentialModel, WorkerModel
from app.services.analysis_service import persist_async_analysis_completion


@dataclass(frozen=True)
class WorkerIdentity:
    credential: WorkerCredentialModel
    worker: WorkerModel


def ensure_worker_api_enabled() -> None:
    settings = get_settings()
    if not settings.jobs_enabled or not settings.worker_api_enabled:
        raise HTTPException(status_code=503, detail="Worker protocol is disabled.")


def authenticate_worker(db: Session, token: str, protocol_version: str | None = None) -> WorkerIdentity:
    ensure_worker_api_enabled()
    credential = verify_worker_credential(db, token)
    if credential is None:
        raise HTTPException(status_code=401, detail="Worker authentication failed.")
    worker = db.get(WorkerModel, credential.worker_id)
    if worker is None:
        raise HTTPException(status_code=401, detail="Worker authentication failed.")
    expected = get_settings().worker_protocol_version
    if worker.protocol_version != expected or (protocol_version is not None and protocol_version != expected):
        raise HTTPException(status_code=409, detail="Worker protocol version is not supported.")
    return WorkerIdentity(credential=credential, worker=worker)


def claim_next_job(db: Session, identity: WorkerIdentity) -> WorkerClaimResponse:
    now = datetime.now(UTC)
    _mark_stale_workers(db, now)
    recover_expired_jobs(db, now=now)
    if _active_worker_jobs(db, identity.worker.id) >= identity.worker.max_concurrency:
        db.commit()
        return WorkerClaimResponse()

    candidates = db.execute(_claim_statement(db, now)).scalars().all()
    eligible = []
    for job in candidates:
        if not _worker_can_execute(identity, job):
            continue
        if not _job_schema_is_supported(job):
            _fail_unsupported_schema_job(db, job)
            continue
        if not _job_is_executable(db, job):
            _fail_revoked_job(db, job)
            continue
        eligible.append(job)
    if not eligible:
        db.commit()
        return WorkerClaimResponse()

    # The least-running tenant wins within the server-priority/availability band.
    job = min(eligible, key=lambda item: (_tenant_running_score(db, item), item.available_at, item.created_at, item.id))
    try:
        move_pending_capacity_to_running(db, job)
    except HTTPException:
        db.commit()
        return WorkerClaimResponse()

    lease_token = f"lease_{token_urlsafe(32)}"
    max_lease_expires_at = _attempt_max_lease_horizon(job, now)
    lease_expires_at = _lease_deadline(job, now, max_lease_expires_at)
    if lease_expires_at <= now:
        _expire_queued_job(db, job)
        db.commit()
        return WorkerClaimResponse()
    generation = job.lease_generation + 1
    transition_job(
        db,
        job,
        "leased",
        worker_id=identity.worker.id,
        message="Job leased to an authenticated worker.",
        metadata={"lease_generation": generation},
    )
    job.lease_generation = generation
    job.leased_by_worker_id = identity.worker.id
    job.lease_token_hash = hash_job_lease_token(lease_token)
    job.lease_expires_at = lease_expires_at
    job.heartbeat_at = now
    job.attempt_count += 1
    job.updated_at = now
    db.add(
        JobAttemptModel(
            id=f"jobattempt_{job.id}_{generation}",
            job_id=job.id,
            attempt_number=job.attempt_count,
            worker_id=identity.worker.id,
            lease_generation=generation,
            started_at=None,
            heartbeat_at=now,
            max_lease_expires_at=max_lease_expires_at,
            outcome="leased",
            created_at=now,
        )
    )
    db.commit()
    return WorkerClaimResponse(
        job=WorkerClaimedJob(
            id=job.id,
            job_type=job.job_type,
            input_schema_version=job.input_schema_version,
            input_json=job.input_json,
            lease_generation=generation,
            lease_token=lease_token,
            lease_expires_at=lease_expires_at,
            deadline_at=job.deadline_at,
        )
    )


def start_job(db: Session, identity: WorkerIdentity, job_id: str, request: WorkerLeaseRequest) -> WorkerMutationResponse:
    job, attempt = _validate_lease(db, identity, job_id, request)
    if job.status != "leased":
        raise HTTPException(status_code=409, detail="Job cannot be started from its current state.")
    transition_job(db, job, "running", worker_id=identity.worker.id, message="Worker started the leased job.")
    attempt.started_at = datetime.now(UTC)
    attempt.outcome = "running"
    db.commit()
    return _mutation(job)


def heartbeat_job(
    db: Session,
    identity: WorkerIdentity,
    job_id: str,
    request: WorkerHeartbeatRequest,
) -> WorkerMutationResponse:
    job, attempt = _validate_lease(db, identity, job_id, request)
    if job.status not in {"leased", "running"}:
        raise HTTPException(status_code=409, detail="Job cannot accept a heartbeat in its current state.")
    now = datetime.now(UTC)
    expires_at = _lease_deadline(job, now, attempt.max_lease_expires_at)
    if expires_at <= now:
        raise HTTPException(status_code=409, detail="Job deadline has elapsed.")
    job.lease_expires_at = expires_at
    job.heartbeat_at = now
    job.updated_at = now
    if request.progress_percent is not None:
        job.progress_percent = request.progress_percent
    attempt.heartbeat_at = now
    append_job_event(
        db,
        job,
        event_type="job.heartbeat",
        message="Worker lease heartbeat accepted.",
        worker_id=identity.worker.id,
        metadata={"lease_generation": job.lease_generation, "progress_percent": job.progress_percent},
    )
    db.commit()
    return _mutation(job)


def report_progress(
    db: Session,
    identity: WorkerIdentity,
    job_id: str,
    request: WorkerProgressRequest,
) -> WorkerMutationResponse:
    job, attempt = _validate_lease(db, identity, job_id, request)
    if job.status != "running":
        raise HTTPException(status_code=409, detail="Job cannot accept progress in its current state.")
    if _looks_sensitive_progress(request.progress_message):
        raise HTTPException(status_code=422, detail="Progress messages cannot contain credentials or secrets.")
    now = datetime.now(UTC)
    job.progress_percent = request.progress_percent
    job.progress_message = request.progress_message
    job.heartbeat_at = now
    job.updated_at = now
    attempt.heartbeat_at = now
    append_job_event(
        db,
        job,
        event_type="job.progress",
        message=request.progress_message,
        worker_id=identity.worker.id,
        metadata={"progress_percent": request.progress_percent, "lease_generation": job.lease_generation},
    )
    db.commit()
    return _mutation(job)


def complete_job(
    db: Session,
    identity: WorkerIdentity,
    job_id: str,
    request: WorkerLeaseRequest,
    result: JobResultEnvelope,
) -> WorkerMutationResponse:
    job, attempt = _validate_lease(db, identity, job_id, request)
    if job.status != "running":
        raise HTTPException(status_code=409, detail="Job cannot be completed from its current state.")
    validate_result_schema(job.job_type, job.input_schema_version, result)
    if job.job_type == "analysis.generate":
        persist_async_analysis_completion(db, job, result.result_json)
        job.result_json = {
            "analysis_request_id": job.input_json["_server_context"]["analysis_request_id"],
            "report_id": job.result_resource_id,
        }
    elif job.job_type == "vast.session.start":
        session = _persist_vast_completion(db, job, result.result_json)
        job.result_json = {
            "vast_session_id": job.result_resource_id,
            "provider_status": result.result_json["provider_status"],
        }
        job.actual_cost_microusd = min(
            job.estimated_cost_microusd,
            int(round((session.hourly_cost_usd or 0) * 1_000_000))
            * get_settings().vast_max_session_minutes
            // 60,
        )
    job.result_schema_version = result.result_schema_version
    job.progress_percent = 100
    job.progress_message = "Worker completed the job."
    transition_job(db, job, "completed", worker_id=identity.worker.id, message="Worker completed the job.")
    attempt.ended_at = datetime.now(UTC)
    attempt.outcome = "completed"
    _clear_lease(job)
    release_running_capacity(db, job)
    db.commit()
    return _mutation(job)


def fail_job(
    db: Session,
    identity: WorkerIdentity,
    job_id: str,
    request: WorkerFailureRequest,
) -> WorkerMutationResponse:
    job, attempt = _validate_lease(db, identity, job_id, request)
    if job.status == "cancel_requested":
        return _cancel_leased_job(db, job, attempt, identity.worker.id)
    if job.status not in {"leased", "running"}:
        raise HTTPException(status_code=409, detail="Job cannot fail from its current state.")
    job.error_code = request.error_code
    job.error_summary = str(redact_sensitive(request.error_summary))[:512]
    attempt.error_code = job.error_code
    attempt.error_summary = job.error_summary
    attempt.ended_at = datetime.now(UTC)
    should_reconcile = request.error_category == "uncertain_external_side_effect"
    if (request.retryable or should_reconcile) and job.attempt_count < job.max_attempts and _deadline_allows_retry(job):
        transition_job(
            db,
            job,
            "retry_wait",
            worker_id=identity.worker.id,
            message=("Worker reported an uncertain provider outcome; reconciliation is required." if should_reconcile else "Worker reported a retryable failure."),
            metadata={"error_code": job.error_code, "error_category": request.error_category},
        )
        attempt.outcome = "retry_wait"
        move_running_capacity_to_pending(db, job)
        job.available_at = datetime.now(UTC) + timedelta(seconds=_retry_delay_seconds(job.attempt_count, job.id))
    else:
        mark_job_artifacts_incomplete(db, job.id)
        _cleanup_provider_for_terminal_job(db, job)
        transition_job(
            db,
            job,
            "dead_letter",
            worker_id=identity.worker.id,
            message="Worker reported a terminal failure.",
            metadata={"error_code": job.error_code},
        )
        attempt.outcome = "dead_letter"
        release_running_capacity(db, job)
    _clear_lease(job)
    db.commit()
    return _mutation(job)


def release_job(db: Session, identity: WorkerIdentity, job_id: str, request: WorkerLeaseRequest) -> WorkerMutationResponse:
    job, attempt = _validate_lease(db, identity, job_id, request)
    if job.status == "cancel_requested":
        return _cancel_leased_job(db, job, attempt, identity.worker.id)
    if job.status not in {"leased", "running"}:
        raise HTTPException(status_code=409, detail="Job cannot be released from its current state.")
    transition_job(db, job, "retry_wait", worker_id=identity.worker.id, message="Worker released the lease for retry.")
    attempt.ended_at = datetime.now(UTC)
    attempt.outcome = "released"
    move_running_capacity_to_pending(db, job)
    job.available_at = datetime.now(UTC) + timedelta(seconds=_retry_delay_seconds(job.attempt_count, job.id))
    _clear_lease(job)
    db.commit()
    return _mutation(job)


def cancellation_status(db: Session, identity: WorkerIdentity, job_id: str) -> WorkerCancellationResponse:
    job = db.execute(
        select(JobModel).where(JobModel.id == job_id).where(JobModel.leased_by_worker_id == identity.worker.id)
    ).scalars().one_or_none()
    if job is None or job.job_type not in identity.credential.allowed_job_types:
        raise HTTPException(status_code=404, detail="Job not found")
    return WorkerCancellationResponse(
        cancellation_requested=job.status == "cancel_requested",
        terminal=job.status in {"completed", "failed", "cancelled", "dead_letter"},
    )


def recover_expired_jobs(db: Session, *, now: datetime | None = None) -> int:
    timestamp = now or datetime.now(UTC)
    statement = (
        select(JobModel)
        .where(JobModel.deleted_at.is_(None))
        .where(
            ((JobModel.status.in_({"leased", "running", "cancel_requested"})) & (JobModel.lease_expires_at <= timestamp))
            | ((JobModel.status.in_({"queued", "retry_wait"})) & (JobModel.queue_expires_at <= timestamp))
        )
        .with_for_update(skip_locked=_is_postgres(db))
    )
    recovered = 0
    for job in db.execute(statement).scalars().all():
        if job.status in {"queued", "retry_wait"}:
            _expire_queued_job(db, job)
        elif job.status == "cancel_requested":
            attempt = _attempt_for_lease(db, job)
            _cancel_leased_job(db, job, attempt, job.leased_by_worker_id, commit=False)
        elif job.attempt_count >= job.max_attempts or not _deadline_allows_retry(job, timestamp):
            attempt = _attempt_for_lease(db, job)
            mark_job_artifacts_incomplete(db, job.id, now=timestamp)
            _cleanup_provider_for_terminal_job(db, job)
            transition_job(db, job, "dead_letter", message="Lease expired after the final worker attempt.")
            if attempt:
                attempt.ended_at = timestamp
                attempt.outcome = "lease_expired_dead_letter"
            release_running_capacity(db, job)
            _clear_lease(job)
        else:
            attempt = _attempt_for_lease(db, job)
            transition_job(db, job, "retry_wait", message="Worker lease expired; job is scheduled for retry.")
            if attempt:
                attempt.ended_at = timestamp
                attempt.outcome = "lease_expired_retry"
            move_running_capacity_to_pending(db, job)
            job.available_at = timestamp + timedelta(seconds=_retry_delay_seconds(job.attempt_count, job.id))
            _clear_lease(job)
        recovered += 1
    return recovered


def recover_durable_jobs(db: Session, *, now: datetime | None = None, dry_run: bool = False) -> dict[str, int]:
    """Recover queue state without requiring another worker to claim a job.

    This command is deliberately safe to schedule from an operations runtime rather
    than a browser or web request. Repeated calls converge on the same state.
    """

    timestamp = now or datetime.now(UTC)
    stale_workers = _mark_stale_workers(db, timestamp)
    expired = recover_expired_jobs(db, now=timestamp)
    authorization_revoked = 0
    cancellation_finalized = 0
    jobs = db.execute(
        select(JobModel)
        .where(JobModel.deleted_at.is_(None))
        .where(JobModel.status.in_({"queued", "retry_wait", "leased", "running", "cancel_requested"}))
        .with_for_update(skip_locked=_is_postgres(db))
    ).scalars().all()
    for job in jobs:
        reason = _job_authorization_reason(db, job)
        if reason is not None and job.status in {"queued", "retry_wait"}:
            _fail_revoked_job(db, job)
            authorization_revoked += 1
        elif reason is not None and job.status in {"leased", "running"}:
            transition_job(
                db,
                job,
                "cancel_requested",
                message="Job execution cancellation requested after authorization revalidation.",
                metadata={"reason": reason},
            )
            job.error_code = "authorization_revoked"
            job.error_summary = "Job authorization was revoked during controlled execution."
            authorization_revoked += 1
        elif job.status == "cancel_requested" and job.leased_by_worker_id is None:
            _cancel_leased_job(db, job, None, None, commit=False)
            cancellation_finalized += 1
    capacity_adjustments = _reconcile_capacity(db, timestamp)
    counts = {
        "expired_jobs": expired,
        "stale_workers": stale_workers,
        "authorization_revoked": authorization_revoked,
        "cancellation_finalized": cancellation_finalized,
        "capacity_adjustments": capacity_adjustments,
    }
    if dry_run:
        db.rollback()
    else:
        db.commit()
    return counts


def _claim_statement(db: Session, now: datetime):
    priority = case((JobModel.priority_class == "admin", 0), (JobModel.priority_class == "elevated", 1), else_=2)
    return (
        select(JobModel)
        .where(JobModel.deleted_at.is_(None))
        .where(JobModel.status.in_({"queued", "retry_wait"}))
        .where(JobModel.available_at <= now)
        .where((JobModel.queue_expires_at.is_(None)) | (JobModel.queue_expires_at > now))
        .where((JobModel.deadline_at.is_(None)) | (JobModel.deadline_at > now))
        .order_by(priority, JobModel.available_at, JobModel.created_at, JobModel.id)
        .limit(get_settings().job_claim_scan_limit)
        .with_for_update(skip_locked=_is_postgres(db))
    )


def _validate_lease(
    db: Session,
    identity: WorkerIdentity,
    job_id: str,
    request: WorkerLeaseRequest,
) -> tuple[JobModel, JobAttemptModel]:
    job = db.execute(select(JobModel).where(JobModel.id == job_id).with_for_update()).scalars().one_or_none()
    if job is None or job.deleted_at is not None or job.job_type not in identity.credential.allowed_job_types:
        raise HTTPException(status_code=404, detail="Job not found")
    now = datetime.now(UTC)
    if (
        job.leased_by_worker_id != identity.worker.id
        or job.lease_generation != request.lease_generation
        or not job.lease_token_hash
        or not constant_time_equal(job.lease_token_hash, hash_job_lease_token(request.lease_token))
        or job.lease_expires_at is None
        or _utc(job.lease_expires_at) <= now
    ):
        raise HTTPException(status_code=409, detail="Worker lease is stale or invalid.")
    attempt = _attempt_for_lease(db, job)
    if attempt is None:
        raise HTTPException(status_code=409, detail="Worker lease attempt is unavailable.")
    authorization_reason = _job_authorization_reason(db, job)
    if authorization_reason is not None:
        if job.status in {"leased", "running"}:
            transition_job(
                db,
                job,
                "cancel_requested",
                message="Job authorization was revoked while a worker held the lease.",
                metadata={"reason": authorization_reason},
            )
            job.error_code = "authorization_revoked"
            job.error_summary = "Job authorization was revoked during controlled execution."
            db.commit()
        raise HTTPException(status_code=409, detail="Job authorization is no longer valid.")
    return job, attempt


def _worker_can_execute(identity: WorkerIdentity, job: JobModel) -> bool:
    return bool(
        job.job_type in identity.credential.allowed_job_types
        and job.job_type in identity.worker.allowed_job_types
        and (identity.worker.organization_id is None or identity.worker.organization_id == job.organization_id)
    )


def _job_is_executable(db: Session, job: JobModel) -> bool:
    return _job_authorization_reason(db, job) is None


def _job_authorization_reason(db: Session, job: JobModel) -> str | None:
    if not job.owner_user_id:
        return "owner_missing"
    owner = db.get(UserModel, job.owner_user_id)
    if owner is None or not owner.is_active or owner.account_status != "active" or owner.deleted_at is not None:
        return "owner_inactive"
    if not job.organization_id:
        return None
    membership = db.execute(
        select(OrganizationMembershipModel)
        .join(OrganizationModel, OrganizationModel.id == OrganizationMembershipModel.organization_id)
        .where(OrganizationMembershipModel.organization_id == job.organization_id)
        .where(OrganizationMembershipModel.user_id == owner.id)
        .where(OrganizationMembershipModel.status == "active")
        .where(OrganizationModel.status == "active")
        .where(OrganizationModel.deleted_at.is_(None))
    ).scalars().one_or_none()
    if membership is None:
        return "organization_membership_removed"
    if membership.role not in {"owner", "admin", "member"}:
        return "organization_role_insufficient"
    return None


def _fail_revoked_job(db: Session, job: JobModel) -> None:
    reason = _job_authorization_reason(db, job) or "authorization_revoked"
    transition_job(
        db,
        job,
        "failed",
        message="Job authorization was revoked before worker execution.",
        metadata={"reason": reason},
    )
    job.error_code = "authorization_revoked"
    job.error_summary = "Job authorization was revoked before worker execution."
    _release_capacity(db, job)


def _job_schema_is_supported(job: JobModel) -> bool:
    try:
        request = job.input_json.get("request") if isinstance(job.input_json, dict) else None
        if not isinstance(request, dict):
            return False
        from app.jobs.registry import validate_submission_schema

        validate_submission_schema(job.job_type, job.input_schema_version, request)
        return True
    except HTTPException:
        return False


def _fail_unsupported_schema_job(db: Session, job: JobModel) -> None:
    transition_job(
        db,
        job,
        "failed",
        message="Job input schema is unsupported and cannot be leased.",
        metadata={"reason": "unsupported_schema"},
    )
    job.error_code = "unsupported_schema"
    job.error_summary = "Job input schema is unsupported and was not executed."
    _release_capacity(db, job)


def _expire_queued_job(db: Session, job: JobModel) -> None:
    transition_job(db, job, "failed", message="Job queue deadline elapsed before worker execution.")
    job.error_code = "queue_expired"
    job.error_summary = "No eligible worker accepted the job before its queue deadline."
    _release_capacity(db, job)


def _cancel_leased_job(
    db: Session,
    job: JobModel,
    attempt: JobAttemptModel | None,
    worker_id: str | None,
    *,
    commit: bool = True,
) -> WorkerMutationResponse:
    mark_job_artifacts_incomplete(db, job.id)
    _cleanup_provider_for_terminal_job(db, job)
    transition_job(db, job, "cancelled", worker_id=worker_id, message="Worker acknowledged job cancellation.")
    if attempt:
        attempt.ended_at = datetime.now(UTC)
        attempt.outcome = "cancelled"
    release_running_capacity(db, job)
    _clear_lease(job)
    if commit:
        db.commit()
    return _mutation(job)


def _attempt_for_lease(db: Session, job: JobModel) -> JobAttemptModel | None:
    return db.execute(
        select(JobAttemptModel)
        .where(JobAttemptModel.job_id == job.id)
        .where(JobAttemptModel.lease_generation == job.lease_generation)
        .with_for_update()
    ).scalars().one_or_none()


def _clear_lease(job: JobModel) -> None:
    job.leased_by_worker_id = None
    job.lease_token_hash = None
    job.lease_expires_at = None
    job.heartbeat_at = None
    job.updated_at = datetime.now(UTC)


def _attempt_max_lease_horizon(job: JobModel, now: datetime) -> datetime:
    horizon = now + timedelta(seconds=get_settings().job_max_lease_extension_seconds)
    if job.deadline_at is not None:
        horizon = min(horizon, _utc(job.deadline_at))
    return horizon


def _lease_deadline(job: JobModel, now: datetime, max_horizon: datetime | None) -> datetime:
    proposed = now + timedelta(seconds=get_settings().job_lease_seconds)
    caps = [proposed]
    if max_horizon is not None:
        caps.append(_utc(max_horizon))
    if job.deadline_at is not None:
        caps.append(_utc(job.deadline_at))
    return min(caps)


def _deadline_allows_retry(job: JobModel, now: datetime | None = None) -> bool:
    if job.deadline_at is None:
        return True
    return _utc(job.deadline_at) > (now or datetime.now(UTC))


def _retry_delay_seconds(attempt_count: int, job_id: str) -> int:
    settings = get_settings()
    base_delay = min(settings.job_retry_max_seconds, settings.job_retry_base_seconds * (2 ** max(attempt_count - 1, 0)))
    jitter_bound = min(max(settings.job_retry_base_seconds, 1), 5)
    jitter = int(hashlib.sha256(f"{job_id}:{attempt_count}".encode("utf-8")).hexdigest()[:4], 16) % jitter_bound
    return min(settings.job_retry_max_seconds, base_delay + jitter)


def _active_worker_jobs(db: Session, worker_id: str) -> int:
    return len(
        db.execute(
            select(JobModel.id)
            .where(JobModel.leased_by_worker_id == worker_id)
            .where(JobModel.status.in_({"leased", "running", "cancel_requested"}))
        ).all()
    )


def _tenant_running_score(db: Session, job: JobModel) -> tuple[int, int]:
    from app.models.job import JobCapacityReservationModel

    user_running = db.execute(
        select(JobCapacityReservationModel.running_count)
        .where(JobCapacityReservationModel.scope_type == "user")
        .where(JobCapacityReservationModel.scope_id == (job.owner_user_id or "deleted"))
    ).scalar_one_or_none() or 0
    org_running = 0
    if job.organization_id:
        org_running = db.execute(
            select(JobCapacityReservationModel.running_count)
            .where(JobCapacityReservationModel.scope_type == "organization")
            .where(JobCapacityReservationModel.scope_id == job.organization_id)
        ).scalar_one_or_none() or 0
    return user_running, org_running


def _mark_stale_workers(db: Session, now: datetime) -> int:
    threshold = now - timedelta(seconds=get_settings().worker_stale_seconds)
    stale = 0
    for worker in db.execute(
        select(WorkerModel)
        .where(WorkerModel.status == "active")
        .where(WorkerModel.last_seen_at.is_not(None))
        .where(WorkerModel.last_seen_at < threshold)
    ).scalars().all():
        worker.status = "stale"
        worker.updated_at = now
        stale += 1
    return stale


def _reconcile_capacity(db: Session, now: datetime) -> int:
    """Make durable counters match non-terminal job state after crashes."""

    from app.jobs.control_service import _capacity_scopes

    desired: dict[tuple[str, str], list[int]] = {}
    active = db.execute(
        select(JobModel)
        .where(JobModel.deleted_at.is_(None))
        .where(JobModel.status.in_({"queued", "retry_wait", "leased", "running", "cancel_requested"}))
    ).scalars().all()
    for job in active:
        for scope_type, scope_id, _, _, _ in _capacity_scopes(job.owner_user_id or "deleted", job.organization_id, job.job_type):
            current = desired.setdefault((scope_type, scope_id), [0, 0, 0])
            if job.status in {"queued", "retry_wait"} or (job.status == "cancel_requested" and job.leased_by_worker_id is None):
                current[0] += 1
            else:
                current[1] += 1
            if scope_type == "global":
                current[2] += job.reserved_cost_microusd
    adjusted = 0
    for record in db.execute(select(JobCapacityReservationModel).with_for_update()).scalars().all():
        pending, running, cost = desired.get((record.scope_type, record.scope_id), [0, 0, 0])
        if (record.pending_count, record.running_count, record.reserved_cost_microusd) != (pending, running, cost):
            record.pending_count = pending
            record.running_count = running
            if record.scope_type == "global":
                record.reserved_cost_microusd = cost
            record.updated_at = now
            adjusted += 1
    return adjusted


def _looks_sensitive_progress(message: str) -> bool:
    lowered = message.lower()
    return any(marker in lowered for marker in ("api_key", "password", "authorization", "credential", "secret"))


def _mutation(job: JobModel) -> WorkerMutationResponse:
    return WorkerMutationResponse(job_id=job.id, status=job.status, lease_expires_at=job.lease_expires_at)


def _persist_vast_completion(db: Session, job: JobModel, result_json: dict) -> VastSessionModel:
    try:
        session_id = result_json["vast_session_id"]
        provider_status = result_json["provider_status"]
        expected_id = job.input_json["_server_context"]["vast_session_id"]
    except (KeyError, TypeError) as exc:
        raise HTTPException(status_code=422, detail="Vast job result is invalid.") from exc
    if not isinstance(session_id, str) or session_id != expected_id or session_id != job.result_resource_id:
        raise HTTPException(status_code=422, detail="Vast job result used an unexpected session identifier.")
    if not isinstance(provider_status, str) or len(provider_status) > 64:
        raise HTTPException(status_code=422, detail="Vast job result is invalid.")
    session = db.get(VastSessionModel, session_id)
    if session is None or session.source_job_id != job.id:
        raise HTTPException(status_code=409, detail="Vast session is not linked to this job.")
    if session.status != provider_status:
        raise HTTPException(status_code=422, detail="Vast job result does not match the durable provider session state.")
    return session


def _cleanup_provider_for_terminal_job(db: Session, job: JobModel) -> None:
    """Best-effort, idempotent teardown for a cancelled or terminal Vast job."""

    if job.job_type != "vast.session.start":
        return
    session = db.execute(
        select(VastSessionModel).where(VastSessionModel.source_job_id == job.id)
    ).scalars().one_or_none()
    if session is None or session.status == "destroyed" or not job.owner_user_id:
        return
    owner = db.get(UserModel, job.owner_user_id)
    if owner is None:
        return
    try:
        from app.llm.vast.lifecycle import destroy_session

        destroy_session(db, user_context(owner), session.id)
    except Exception:
        # The session lifecycle records its own cleanup failure. Job cancellation must
        # remain terminal even if the remote provider cannot be reached.
        return


def _is_postgres(db: Session) -> bool:
    return bool(db.bind and db.bind.dialect.name == "postgresql")


def _utc(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)
