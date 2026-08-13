from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.service import user_context
from app.db.session import SessionLocal
from app.jobs.cancellation import CancellationContext
from app.jobs.errors import JobErrorCategory, JobExecutionError
from app.jobs.schemas import JobResultEnvelope, WorkerClaimedJob
from app.models.scheduled_monitoring import MonitoringScheduleModel, MonitoringScheduleOccurrenceModel
from app.models.user import UserModel
from app.models.watchlist_item import WatchlistItemModel
from app.watchlist.service import evaluate_watchlist_item


class WatchlistEvaluationJobExecutor:
    """Execute only the dispatcher-derived, owner-private watchlist target."""

    def __init__(self, session_factory: Callable[[], Session] = SessionLocal) -> None:
        self._session_factory = session_factory

    def execute(self, job: WorkerClaimedJob, cancellation: CancellationContext | None = None) -> JobResultEnvelope:
        cancellation = cancellation or CancellationContext()
        schedule_id, occurrence_id, watchlist_item_id, owner_user_id = _job_input(job)
        cancellation.raise_if_cancelled()
        with self._session_factory() as db:
            # Lock in the same owner -> schedule -> target order used by the
            # dispatcher and account disposal path to avoid inverse lock waits.
            owner = db.execute(
                select(UserModel).where(UserModel.id == owner_user_id).with_for_update()
            ).scalars().one_or_none()
            schedule = db.execute(
                select(MonitoringScheduleModel).where(MonitoringScheduleModel.id == schedule_id).with_for_update()
            ).scalars().one_or_none()
            occurrence = db.execute(
                select(MonitoringScheduleOccurrenceModel)
                .where(MonitoringScheduleOccurrenceModel.id == occurrence_id)
                .where(MonitoringScheduleOccurrenceModel.schedule_id == schedule_id)
                .with_for_update()
            ).scalars().one_or_none()
            target = db.execute(
                select(WatchlistItemModel)
                .where(WatchlistItemModel.id == watchlist_item_id)
                .where(WatchlistItemModel.owner_user_id == (owner.id if owner is not None else ""))
                .where(WatchlistItemModel.organization_id.is_(None))
                .where(WatchlistItemModel.visibility == "private")
                .where(WatchlistItemModel.anonymous_session_id.is_(None))
                .where(WatchlistItemModel.deleted_at.is_(None))
                .where(WatchlistItemModel.enabled.is_(True))
                .with_for_update()
            ).scalars().one_or_none()
            if (
                schedule is None
                or occurrence is None
                or occurrence.job_id != job.id
                or schedule.status != "active"
                or schedule.deleted_at is not None
            ):
                _mark_cancelled(db, occurrence)
                raise JobExecutionError(JobErrorCategory.CANCELLATION, "schedule_inactive", "Scheduled monitoring is no longer active.")
            if (
                owner is None
                or schedule.owner_user_id != owner_user_id
                or not owner.is_active
                or owner.account_status != "active"
                or owner.deleted_at is not None
            ):
                _mark_denied(db, occurrence, "authorization_revoked")
                raise JobExecutionError(JobErrorCategory.PERMANENT_AUTHORIZATION, "authorization_revoked", "Schedule owner is unavailable.")
            if target is None:
                _mark_denied(db, occurrence, "target_unavailable")
                raise JobExecutionError(JobErrorCategory.PERMANENT_AUTHORIZATION, "target_unavailable", "Scheduled watchlist target is unavailable.")
            occurrence.status = "running"
            occurrence.updated_at = _utc_now()
            db.commit()

            cancellation.raise_if_cancelled()
            try:
                evaluation = evaluate_watchlist_item(watchlist_item_id, db, user_context(owner, auth_enabled=True))
            except HTTPException as exc:
                with self._session_factory() as failure_db:
                    failed_occurrence = failure_db.execute(
                        select(MonitoringScheduleOccurrenceModel)
                        .where(MonitoringScheduleOccurrenceModel.id == occurrence_id)
                        .with_for_update()
                    ).scalars().one_or_none()
                    _mark_denied(failure_db, failed_occurrence, "target_unavailable")
                raise JobExecutionError(
                    JobErrorCategory.PERMANENT_AUTHORIZATION,
                    "target_unavailable",
                    "Scheduled watchlist target is unavailable.",
                ) from exc
            cancellation.raise_if_cancelled()

            refreshed = db.execute(
                select(MonitoringScheduleOccurrenceModel)
                .where(MonitoringScheduleOccurrenceModel.id == occurrence_id)
                .with_for_update()
            ).scalars().one_or_none()
            if refreshed is not None:
                refreshed.status = "completed"
                refreshed.completed_at = _utc_now()
                refreshed.updated_at = refreshed.completed_at
                db.commit()
            return JobResultEnvelope(
                result_schema_version="watchlist.evaluate.v1",
                result_json={
                    "watchlist_item_id": watchlist_item_id,
                    "evaluated_rule_count": len(evaluation.evaluated_rules),
                    "created_alert_count": len(evaluation.created_alerts),
                    "scheduled_for": _utc_timestamp(occurrence.scheduled_for).isoformat(),
                },
            )


def _job_input(job: WorkerClaimedJob) -> tuple[str, str, str, str]:
    try:
        request = job.input_json["request"]
        context = job.input_json["_server_context"]
        schedule_id = context["schedule_id"]
        occurrence_id = context["schedule_occurrence_id"]
        owner_user_id = context["owner_user_id"]
        watchlist_item_id = request["watchlist_item_id"]
    except (KeyError, TypeError) as exc:
        raise JobExecutionError(JobErrorCategory.PERMANENT_INPUT, "schedule_input_invalid", "Scheduled monitoring input is invalid.") from exc
    if not all(
        isinstance(value, str) and value
        for value in (schedule_id, occurrence_id, watchlist_item_id, owner_user_id)
    ):
        raise JobExecutionError(JobErrorCategory.PERMANENT_INPUT, "schedule_input_invalid", "Scheduled monitoring input is invalid.")
    return schedule_id, occurrence_id, watchlist_item_id, owner_user_id


def _mark_denied(db: Session, occurrence: MonitoringScheduleOccurrenceModel | None, reason: str) -> None:
    if occurrence is not None:
        occurrence.status = "denied"
        occurrence.reason = reason
        occurrence.completed_at = _utc_now()
        occurrence.updated_at = occurrence.completed_at
    db.commit()


def _mark_cancelled(db: Session, occurrence: MonitoringScheduleOccurrenceModel | None) -> None:
    if occurrence is not None:
        occurrence.status = "cancelled"
        occurrence.reason = "schedule_inactive"
        occurrence.completed_at = _utc_now()
        occurrence.updated_at = occurrence.completed_at
    db.commit()


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _utc_timestamp(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
