from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.schemas import UserContext
from app.auth.service import record_audit_event, user_context
from app.core.config import get_settings
from app.jobs.constants import TERMINAL_JOB_STATUSES
from app.jobs.control_service import _release_capacity, submit_job
from app.jobs.schemas import JobSubmissionRequest
from app.jobs.state import transition_job
from app.models.job import JobModel
from app.models.scheduled_monitoring import MonitoringScheduleModel, MonitoringScheduleOccurrenceModel
from app.models.user import UserModel
from app.models.watchlist_item import WatchlistItemModel
from app.scheduling.calendar import first_due_after, initial_due_after, latest_due_not_after
from app.scheduling.schemas import (
    MonitoringScheduleActionResponse,
    MonitoringScheduleCreateRequest,
    MonitoringScheduleDispatchSummary,
    MonitoringScheduleResponse,
    MonitoringScheduleRunResponse,
)


logger = logging.getLogger("defi_copilot.scheduling")

ACTIVE_SCHEDULE_LIMIT = 5
OVERDUE_SKIP_AFTER = timedelta(hours=24)


def create_schedule(
    db: Session,
    actor: UserContext,
    request: MonitoringScheduleCreateRequest,
    *,
    now: datetime | None = None,
) -> MonitoringScheduleActionResponse:
    timestamp = _utc_now(now)
    _lock_active_owner(db, actor.id)
    _validate_owned_watchlist_target(db, actor.id, request.target_id)
    active_count = _active_schedule_count(db, actor.id)
    if active_count >= ACTIVE_SCHEDULE_LIMIT:
        raise HTTPException(status_code=409, detail="A user may have at most five active monitoring schedules")
    schedule = MonitoringScheduleModel(
        id=f"sched_{uuid4().hex[:12]}",
        owner_user_id=actor.id,
        target_type=request.target_type,
        target_id=request.target_id,
        cadence=request.cadence,
        timezone=request.timezone,
        status="active",
        next_due_at=initial_due_after(timestamp, request.cadence, request.timezone),
        created_at=timestamp,
        updated_at=timestamp,
    )
    db.add(schedule)
    record_audit_event(
        db,
        actor.id,
        "schedule.created",
        "monitoring_schedule",
        schedule.id,
        {"target_type": schedule.target_type, "cadence": schedule.cadence, "timezone": schedule.timezone},
        commit=False,
    )
    db.commit()
    db.refresh(schedule)
    return MonitoringScheduleActionResponse(schedule=schedule_response(schedule))


def list_schedules(db: Session, actor: UserContext) -> list[MonitoringScheduleResponse]:
    records = db.execute(
        select(MonitoringScheduleModel)
        .where(MonitoringScheduleModel.owner_user_id == actor.id)
        .where(MonitoringScheduleModel.deleted_at.is_(None))
        .order_by(MonitoringScheduleModel.created_at.desc(), MonitoringScheduleModel.id.desc())
    ).scalars().all()
    return [schedule_response(record) for record in records]


def get_schedule(db: Session, actor: UserContext, schedule_id: str, *, include_deleted: bool = False) -> MonitoringScheduleModel:
    statement = (
        select(MonitoringScheduleModel)
        .where(MonitoringScheduleModel.id == schedule_id)
        .where(MonitoringScheduleModel.owner_user_id == actor.id)
    )
    if not include_deleted:
        statement = statement.where(MonitoringScheduleModel.deleted_at.is_(None))
    schedule = db.execute(statement).scalars().one_or_none()
    if schedule is None:
        raise HTTPException(status_code=404, detail="Monitoring schedule not found")
    return schedule


def pause_schedule(
    db: Session,
    actor: UserContext,
    schedule_id: str,
    *,
    now: datetime | None = None,
) -> MonitoringScheduleActionResponse:
    timestamp = _utc_now(now)
    _lock_active_owner(db, actor.id)
    schedule = _locked_owned_schedule(db, actor.id, schedule_id)
    if schedule.status == "active":
        schedule.status = "paused"
        schedule.paused_at = timestamp
        schedule.updated_at = timestamp
        _cancel_schedule_work(db, schedule, actor.id, "schedule_paused", timestamp)
        record_audit_event(db, actor.id, "schedule.paused", "monitoring_schedule", schedule.id, commit=False)
        db.commit()
        db.refresh(schedule)
    return MonitoringScheduleActionResponse(schedule=schedule_response(schedule))


def resume_schedule(
    db: Session,
    actor: UserContext,
    schedule_id: str,
    *,
    now: datetime | None = None,
) -> MonitoringScheduleActionResponse:
    timestamp = _utc_now(now)
    _lock_active_owner(db, actor.id)
    schedule = _locked_owned_schedule(db, actor.id, schedule_id)
    if schedule.status == "paused":
        _validate_owned_watchlist_target(db, actor.id, schedule.target_id)
        if _active_schedule_count(db, actor.id) >= ACTIVE_SCHEDULE_LIMIT:
            raise HTTPException(status_code=409, detail="A user may have at most five active monitoring schedules")
        schedule.status = "active"
        schedule.paused_at = None
        schedule.next_due_at = first_due_after(timestamp, schedule.cadence, schedule.timezone, schedule.next_due_at)
        schedule.updated_at = timestamp
        record_audit_event(db, actor.id, "schedule.resumed", "monitoring_schedule", schedule.id, commit=False)
        db.commit()
        db.refresh(schedule)
    return MonitoringScheduleActionResponse(schedule=schedule_response(schedule))


def delete_schedule(
    db: Session,
    actor: UserContext,
    schedule_id: str,
    *,
    now: datetime | None = None,
) -> MonitoringScheduleActionResponse:
    timestamp = _utc_now(now)
    _lock_active_owner(db, actor.id)
    schedule = _locked_owned_schedule(db, actor.id, schedule_id, include_deleted=True)
    if schedule.status != "deleted":
        schedule.status = "deleted"
        schedule.deleted_at = timestamp
        schedule.paused_at = timestamp
        schedule.updated_at = timestamp
        _cancel_schedule_work(db, schedule, actor.id, "schedule_deleted", timestamp)
        record_audit_event(db, actor.id, "schedule.deleted", "monitoring_schedule", schedule.id, commit=False)
        db.commit()
        db.refresh(schedule)
    return MonitoringScheduleActionResponse(schedule=schedule_response(schedule))


def list_schedule_runs(
    db: Session,
    actor: UserContext,
    schedule_id: str,
    *,
    limit: int = 50,
) -> list[MonitoringScheduleRunResponse]:
    schedule = get_schedule(db, actor, schedule_id, include_deleted=True)
    records = db.execute(
        select(MonitoringScheduleOccurrenceModel)
        .where(MonitoringScheduleOccurrenceModel.schedule_id == schedule.id)
        .order_by(MonitoringScheduleOccurrenceModel.scheduled_for.desc(), MonitoringScheduleOccurrenceModel.id.desc())
        .limit(limit)
    ).scalars().all()
    jobs = {
        item.id: item
        for item in db.execute(
            select(JobModel).where(JobModel.id.in_([record.job_id for record in records if record.job_id]))
        ).scalars().all()
    }
    return [_occurrence_response(record, jobs.get(record.job_id or "")) for record in records]


def dispatch_due_schedules(
    db: Session,
    *,
    now: datetime | None = None,
) -> MonitoringScheduleDispatchSummary:
    """Claim and dispatch due schedules from PostgreSQL in one durable transaction."""

    if not get_settings().schedule_dispatch_enabled:
        return MonitoringScheduleDispatchSummary(status="disabled", claimed=0, queued=0, denied=0, missed=0, failures=0)
    timestamp = _utc_now(now)
    candidate_ids = db.execute(
        select(MonitoringScheduleModel.id)
        .where(MonitoringScheduleModel.status == "active")
        .where(MonitoringScheduleModel.deleted_at.is_(None))
        .where(MonitoringScheduleModel.next_due_at <= timestamp)
        .order_by(MonitoringScheduleModel.next_due_at, MonitoringScheduleModel.id)
        .limit(get_settings().schedule_dispatch_batch_size)
    ).scalars().all()
    # Do not hold a discovery transaction while individual schedule claims run.
    # Every claim below locks owner first, then schedule, matching account lifecycle
    # operations and preventing inverse user/schedule lock ordering.
    db.commit()
    counts = {"claimed": 0, "queued": 0, "denied": 0, "missed": 0, "failures": 0}
    for schedule_id in candidate_ids:
        try:
            with db.begin():
                candidate = db.execute(
                    select(MonitoringScheduleModel).where(MonitoringScheduleModel.id == schedule_id)
                ).scalars().one_or_none()
                if candidate is None:
                    continue
                owner = db.execute(
                    select(UserModel)
                    .where(UserModel.id == candidate.owner_user_id)
                    .with_for_update(skip_locked=True)
                ).scalars().one_or_none()
                if owner is None:
                    continue
                schedule = db.execute(
                    select(MonitoringScheduleModel)
                    .where(MonitoringScheduleModel.id == schedule_id)
                    .where(MonitoringScheduleModel.status == "active")
                    .where(MonitoringScheduleModel.deleted_at.is_(None))
                    .where(MonitoringScheduleModel.next_due_at <= timestamp)
                    .with_for_update(skip_locked=True)
                ).scalars().one_or_none()
                if schedule is None:
                    continue
                outcome = _dispatch_locked_schedule(db, schedule, owner, timestamp)
            counts["claimed"] += 1
            counts[outcome] += 1
        except Exception:  # Keep one malformed schedule from blocking others.
            logger.exception("Durable schedule dispatch failed", extra={"schedule_id": schedule_id})
            counts["failures"] += 1
    return MonitoringScheduleDispatchSummary(status="completed", **counts)


def dispose_schedules_for_account_deletion(db: Session, user_id: str, *, now: datetime | None = None) -> int:
    timestamp = _utc_now(now)
    schedules = db.execute(
        select(MonitoringScheduleModel)
        .where(MonitoringScheduleModel.owner_user_id == user_id)
        .where(MonitoringScheduleModel.deleted_at.is_(None))
        .with_for_update()
    ).scalars().all()
    for schedule in schedules:
        schedule.status = "deleted"
        schedule.deleted_at = timestamp
        schedule.paused_at = timestamp
        schedule.updated_at = timestamp
        _cancel_schedule_work(db, schedule, user_id, "owner_account_deleted", timestamp)
    db.flush()
    return len(schedules)


def cleanup_expired_schedule_history(db: Session, *, now: datetime | None = None, apply: bool = False) -> dict[str, int]:
    timestamp = _utc_now(now)
    retention = timedelta(days=get_settings().schedule_history_retention_days)
    expired = db.execute(
        select(MonitoringScheduleOccurrenceModel)
        .where(MonitoringScheduleOccurrenceModel.expires_at <= timestamp)
    ).scalars().all()
    deleted_schedules = db.execute(
        select(MonitoringScheduleModel)
        .where(MonitoringScheduleModel.deleted_at.is_not(None))
        .where(MonitoringScheduleModel.deleted_at <= timestamp - retention)
    ).scalars().all()
    if apply:
        for occurrence in expired:
            db.delete(occurrence)
        db.flush()
        for schedule in deleted_schedules:
            remaining = db.execute(
                select(MonitoringScheduleOccurrenceModel.id).where(
                    MonitoringScheduleOccurrenceModel.schedule_id == schedule.id
                )
            ).first()
            if remaining is None:
                db.delete(schedule)
        db.flush()
    return {"expired_schedule_occurrences": len(expired), "deleted_schedules_ready_for_retention": len(deleted_schedules)}


def _dispatch_locked_schedule(
    db: Session,
    schedule: MonitoringScheduleModel,
    owner: UserModel,
    now: datetime,
) -> str:
    if schedule.status != "active" or schedule.deleted_at is not None:
        return "denied"
    # SQLite returns timezone columns as naive values while PostgreSQL preserves
    # the offset. Treat persisted schedule instants as UTC on both backends.
    original_due = _utc_now(schedule.next_due_at)
    if now - original_due > OVERDUE_SKIP_AFTER:
        schedule.next_due_at = first_due_after(now, schedule.cadence, schedule.timezone, original_due)
        schedule.updated_at = now
        _new_occurrence(schedule, original_due, "missed", "overdue_more_than_24_hours", now, db)
        record_audit_event(
            db, schedule.owner_user_id, "schedule.run_missed", "monitoring_schedule", schedule.id,
            {"reason": "overdue_more_than_24_hours"}, commit=False,
        )
        return "missed"

    scheduled_for, next_due, coalesced = latest_due_not_after(original_due, schedule.cadence, schedule.timezone, now)
    occurrence = _new_occurrence(
        schedule,
        scheduled_for,
        "claimed",
        "coalesced_missed_runs" if coalesced else None,
        now,
        db,
    )
    schedule.next_due_at = next_due
    schedule.last_dispatched_at = now
    schedule.updated_at = now
    if owner.id != schedule.owner_user_id or not owner.is_active or owner.account_status != "active" or owner.deleted_at is not None:
        occurrence.status = "denied"
        occurrence.reason = "authorization_revoked"
        occurrence.updated_at = now
        return "denied"
    target = _owned_watchlist_target(db, owner.id, schedule.target_id)
    if target is None:
        occurrence.status = "denied"
        occurrence.reason = "target_unavailable"
        occurrence.updated_at = now
        return "denied"
    try:
        # A failed reservation must roll back its quota and capacity writes while
        # allowing the durable occurrence to record the server-derived denial.
        with db.begin_nested():
            job, _replayed = submit_job(
                db,
                user_context(owner, auth_enabled=True),
                JobSubmissionRequest(
                    job_type="watchlist.evaluate",
                    input_schema_version="watchlist.evaluate.v1",
                    input_json={"watchlist_item_id": target.id},
                ),
                _occurrence_idempotency_key(schedule.id, scheduled_for),
                allow_scheduled_watchlist=True,
                commit=False,
                extra_server_context={"schedule_id": schedule.id, "schedule_occurrence_id": occurrence.id},
            )
    except HTTPException as exc:
        db.refresh(occurrence)
        occurrence.status = "denied"
        occurrence.reason = _denial_reason(exc.status_code)
        occurrence.updated_at = now
        return "denied"
    job.result_resource_type = "watchlist_item"
    job.result_resource_id = target.id
    occurrence.status = "queued"
    occurrence.job_id = job.id
    occurrence.dispatched_at = now
    occurrence.updated_at = now
    record_audit_event(
        db,
        owner.id,
        "schedule.dispatched",
        "monitoring_schedule",
        schedule.id,
        {"job_type": job.job_type, "occurrence_id": occurrence.id},
        commit=False,
    )
    return "queued"


def _new_occurrence(
    schedule: MonitoringScheduleModel,
    scheduled_for: datetime,
    status: str,
    reason: str | None,
    now: datetime,
    db: Session,
) -> MonitoringScheduleOccurrenceModel:
    occurrence = MonitoringScheduleOccurrenceModel(
        id=f"schedrun_{uuid4().hex[:12]}",
        schedule_id=schedule.id,
        scheduled_for=scheduled_for,
        status=status,
        reason=reason,
        claimed_at=now,
        expires_at=scheduled_for + timedelta(days=get_settings().schedule_history_retention_days),
        created_at=now,
        updated_at=now,
    )
    db.add(occurrence)
    db.flush()
    return occurrence


def _cancel_schedule_work(
    db: Session,
    schedule: MonitoringScheduleModel,
    actor_user_id: str,
    reason: str,
    now: datetime,
) -> None:
    pairs = db.execute(
        select(MonitoringScheduleOccurrenceModel, JobModel)
        .join(JobModel, JobModel.id == MonitoringScheduleOccurrenceModel.job_id)
        .where(MonitoringScheduleOccurrenceModel.schedule_id == schedule.id)
        .where(JobModel.status.not_in(TERMINAL_JOB_STATUSES))
        .with_for_update()
    ).all()
    for occurrence, job in pairs:
        if job.status in {"queued", "retry_wait"}:
            transition_job(
                db, job, "cancel_requested", actor_user_id=actor_user_id,
                message="Scheduled monitoring work was cancelled by schedule lifecycle.", metadata={"reason": reason},
            )
            transition_job(
                db, job, "cancelled", actor_user_id=actor_user_id,
                message="Queued scheduled monitoring work was cancelled before execution.", metadata={"reason": reason},
            )
            _release_capacity(db, job)
            occurrence.status = "cancelled"
            occurrence.completed_at = now
        elif job.status in {"leased", "running"}:
            transition_job(
                db, job, "cancel_requested", actor_user_id=actor_user_id,
                message="Scheduled monitoring work was cancelled by schedule lifecycle.", metadata={"reason": reason},
            )
            occurrence.status = "cancel_requested"
        else:
            occurrence.status = "cancel_requested"
        occurrence.reason = reason
        occurrence.updated_at = now
    for occurrence in db.execute(
        select(MonitoringScheduleOccurrenceModel)
        .where(MonitoringScheduleOccurrenceModel.schedule_id == schedule.id)
        .where(MonitoringScheduleOccurrenceModel.status == "claimed")
        .with_for_update()
    ).scalars().all():
        occurrence.status = "cancelled"
        occurrence.reason = reason
        occurrence.completed_at = now
        occurrence.updated_at = now
    db.flush()


def _lock_active_owner(db: Session, owner_user_id: str) -> UserModel:
    owner = db.execute(select(UserModel).where(UserModel.id == owner_user_id).with_for_update()).scalars().one_or_none()
    if owner is None or not owner.is_active or owner.account_status != "active" or owner.deleted_at is not None:
        raise HTTPException(status_code=403, detail="Schedule owner is unavailable")
    return owner


def _active_schedule_count(db: Session, owner_user_id: str) -> int:
    return len(
        db.execute(
            select(MonitoringScheduleModel.id)
            .where(MonitoringScheduleModel.owner_user_id == owner_user_id)
            .where(MonitoringScheduleModel.status == "active")
            .where(MonitoringScheduleModel.deleted_at.is_(None))
        ).scalars().all()
    )


def _locked_owned_schedule(db: Session, owner_user_id: str, schedule_id: str, *, include_deleted: bool = False) -> MonitoringScheduleModel:
    statement = (
        select(MonitoringScheduleModel)
        .where(MonitoringScheduleModel.id == schedule_id)
        .where(MonitoringScheduleModel.owner_user_id == owner_user_id)
        .with_for_update()
    )
    if not include_deleted:
        statement = statement.where(MonitoringScheduleModel.deleted_at.is_(None))
    schedule = db.execute(statement).scalars().one_or_none()
    if schedule is None:
        raise HTTPException(status_code=404, detail="Monitoring schedule not found")
    return schedule


def _validate_owned_watchlist_target(db: Session, owner_user_id: str, target_id: str) -> WatchlistItemModel:
    target = _owned_watchlist_target(db, owner_user_id, target_id)
    if target is None:
        raise HTTPException(status_code=404, detail="Watchlist target not found")
    return target


def _owned_watchlist_target(db: Session, owner_user_id: str, target_id: str) -> WatchlistItemModel | None:
    return db.execute(
        select(WatchlistItemModel)
        .where(WatchlistItemModel.id == target_id)
        .where(WatchlistItemModel.owner_user_id == owner_user_id)
        .where(WatchlistItemModel.organization_id.is_(None))
        .where(WatchlistItemModel.visibility == "private")
        .where(WatchlistItemModel.anonymous_session_id.is_(None))
        .where(WatchlistItemModel.deleted_at.is_(None))
        .where(WatchlistItemModel.enabled.is_(True))
        .with_for_update()
    ).scalars().one_or_none()


def schedule_response(schedule: MonitoringScheduleModel) -> MonitoringScheduleResponse:
    return MonitoringScheduleResponse(
        id=schedule.id,
        target_type="watchlist.evaluate",
        target_id=schedule.target_id,
        cadence=schedule.cadence,
        timezone=schedule.timezone,
        status=schedule.status,
        next_due_at=schedule.next_due_at,
        paused_at=schedule.paused_at,
        last_dispatched_at=schedule.last_dispatched_at,
        created_at=schedule.created_at,
        updated_at=schedule.updated_at,
        dispatch_enabled=get_settings().schedule_dispatch_enabled,
    )


def _occurrence_response(record: MonitoringScheduleOccurrenceModel, job: JobModel | None) -> MonitoringScheduleRunResponse:
    status = record.status
    completed_at = record.completed_at
    if job is not None:
        if job.status in {"queued", "retry_wait"}:
            status = "queued"
        elif job.status in {"leased", "running"}:
            status = "running"
        elif job.status == "cancel_requested":
            status = "cancel_requested"
        elif job.status == "completed":
            status = "completed"
            completed_at = job.completed_at
        elif job.status == "cancelled":
            status = "cancelled"
            completed_at = job.completed_at or job.updated_at
        elif job.status in {"failed", "dead_letter"}:
            status = "denied" if job.error_code == "authorization_revoked" else "failed"
            completed_at = job.failed_at
    return MonitoringScheduleRunResponse(
        id=record.id,
        scheduled_for=record.scheduled_for,
        status=status,
        reason=record.reason,
        job_id=record.job_id,
        job_status=job.status if job is not None else None,
        claimed_at=record.claimed_at,
        dispatched_at=record.dispatched_at,
        completed_at=completed_at,
        created_at=record.created_at,
    )


def _occurrence_idempotency_key(schedule_id: str, scheduled_for: datetime) -> str:
    return f"schedule:{schedule_id}:{scheduled_for.astimezone(UTC).isoformat()}"


def _denial_reason(status_code: int) -> str:
    if status_code == 429:
        return "quota_or_capacity_denied"
    if status_code in {401, 403, 404}:
        return "authorization_or_target_denied"
    return "dispatch_rejected"


def _utc_now(value: datetime | None) -> datetime:
    timestamp = value or datetime.now(UTC)
    return timestamp.replace(tzinfo=UTC) if timestamp.tzinfo is None else timestamp.astimezone(UTC)
