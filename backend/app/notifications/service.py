from __future__ import annotations

import base64
import binascii
import json
from datetime import UTC, datetime, time, timedelta
from uuid import uuid4
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import HTTPException
from sqlalchemy import and_, delete, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.notification import NotificationModel, NotificationPreferenceModel
from app.notifications.registry import (
    CATEGORIES,
    MANDATORY_CATEGORIES,
    SEVERITIES,
    SEVERITY_RANK,
    SUPPRESSIBLE_CATEGORIES,
    NotificationTemplate,
    template_for,
)
from app.notifications.schemas import (
    NotificationPreferenceResponse,
    NotificationPreferenceUpdateRequest,
    NotificationResponse,
)

RETENTION_DAYS = 30
DEFAULT_TIMEZONE = "UTC"
DEFAULT_DIGEST_HOUR = 9


def emit_notification_intent(
    db: Session,
    *,
    owner_user_id: str | None,
    template_id: str,
    source_id: str,
    idempotency_key: str,
    organization_id: str | None = None,
    occurred_at: datetime | None = None,
    commit: bool = False,
) -> tuple[NotificationModel | None, bool]:
    if owner_user_id is None:
        return None, False
    template = template_for(template_id)
    timestamp = _utc(occurred_at or datetime.now(UTC))
    preference = get_or_create_preferences(db, owner_user_id, commit=False)
    policy_outcome, available_at = _policy_outcome(preference, template, timestamp)
    record = None
    try:
        with db.begin_nested():
            record = NotificationModel(
                id=f"notif_{uuid4().hex[:12]}",
                owner_user_id=owner_user_id,
                organization_id=organization_id,
                category=template.category,
                severity=template.severity,
                template_id=template.template_id,
                title=template.title,
                body=template.body,
                source_type=template.source_type,
                source_id=source_id,
                idempotency_key=idempotency_key,
                navigation_json={"path": template.path, "source_type": template.source_type, "source_id": source_id},
                policy_outcome=policy_outcome,
                available_at=available_at,
                created_at=timestamp,
                updated_at=timestamp,
                expires_at=timestamp + timedelta(days=RETENTION_DAYS),
            )
            db.add(record)
            db.flush()
    except IntegrityError:
        existing = db.execute(
            select(NotificationModel)
            .where(NotificationModel.owner_user_id == owner_user_id)
            .where(NotificationModel.idempotency_key == idempotency_key)
        ).scalars().one_or_none()
        return existing, True
    if commit:
        db.commit()
        db.refresh(record)
    return record, False


def emit_watchlist_alert_notification(db: Session, *, owner_user_id: str | None, alert_id: str, severity: str, occurred_at: datetime) -> None:
    template_id = "monitoring.risk_alert.critical" if severity == "critical" else "monitoring.risk_alert.opened"
    emit_notification_intent(
        db,
        owner_user_id=owner_user_id,
        template_id=template_id,
        source_id=alert_id,
        idempotency_key=f"alert_event:{alert_id}:opened",
        occurred_at=occurred_at,
        commit=False,
    )


def emit_schedule_notification(db: Session, *, owner_user_id: str, occurrence_id: str, status: str, occurred_at: datetime) -> None:
    template_id = {
        "queued": "schedule.status.queued",
        "missed": "schedule.status.missed",
        "denied": "schedule.status.denied",
        "completed": "schedule.status.completed",
        "failed": "schedule.status.failed",
    }.get(status)
    if template_id is None:
        return
    emit_notification_intent(
        db,
        owner_user_id=owner_user_id,
        template_id=template_id,
        source_id=occurrence_id,
        idempotency_key=f"schedule_occurrence:{occurrence_id}:{status}",
        occurred_at=occurred_at,
        commit=False,
    )


def emit_job_notification(db: Session, *, owner_user_id: str | None, organization_id: str | None, job_id: str, status: str, occurred_at: datetime) -> None:
    template_id = {
        "completed": "job.status.completed",
        "failed": "job.status.failed",
        "cancelled": "job.status.cancelled",
        "dead_letter": "job.status.dead_letter",
    }.get(status)
    if template_id is None:
        return
    emit_notification_intent(
        db,
        owner_user_id=owner_user_id,
        organization_id=organization_id,
        template_id=template_id,
        source_id=job_id,
        idempotency_key=f"job:{job_id}:{status}",
        occurred_at=occurred_at,
        commit=False,
    )


def get_or_create_preferences(db: Session, user_id: str, *, commit: bool = True) -> NotificationPreferenceModel:
    record = db.execute(
        select(NotificationPreferenceModel).where(NotificationPreferenceModel.user_id == user_id)
    ).scalars().one_or_none()
    if record is not None:
        return record
    now = datetime.now(UTC)
    record = NotificationPreferenceModel(
        id=f"notpref_{uuid4().hex[:12]}",
        user_id=user_id,
        category_enabled_json=_default_categories(),
        minimum_severity_json={category: "informational" for category in CATEGORIES},
        timezone=DEFAULT_TIMEZONE,
        daily_digest_enabled=False,
        created_at=now,
        updated_at=now,
    )
    try:
        # Preference initialization is auxiliary to the authoritative source
        # transaction. A unique conflict must roll back only this savepoint.
        with db.begin_nested():
            db.add(record)
            db.flush()
    except IntegrityError:
        record = db.execute(
            select(NotificationPreferenceModel).where(NotificationPreferenceModel.user_id == user_id)
        ).scalars().one_or_none()
        if record is None:
            raise
    if commit:
        db.commit()
        db.refresh(record)
    return record


def preference_response(record: NotificationPreferenceModel) -> NotificationPreferenceResponse:
    return NotificationPreferenceResponse(
        categories={category: bool(record.category_enabled_json.get(category, category in MANDATORY_CATEGORIES)) for category in CATEGORIES},
        minimum_severity={category: record.minimum_severity_json.get(category, "informational") for category in CATEGORIES},
        timezone=record.timezone,
        quiet_hours_start=record.quiet_hours_start,
        quiet_hours_end=record.quiet_hours_end,
        daily_digest_enabled=record.daily_digest_enabled,
        mandatory_categories=sorted(MANDATORY_CATEGORIES),
    )


def update_preferences(
    db: Session,
    user_id: str,
    request: NotificationPreferenceUpdateRequest,
) -> NotificationPreferenceResponse:
    record = get_or_create_preferences(db, user_id, commit=False)
    if request.timezone is not None:
        _validate_timezone(request.timezone)
        record.timezone = request.timezone
    categories = dict(record.category_enabled_json)
    if request.categories is not None:
        for category, enabled in request.categories.items():
            categories[category] = True if category in MANDATORY_CATEGORIES else bool(enabled)
    for category in MANDATORY_CATEGORIES:
        categories[category] = True
    record.category_enabled_json = categories
    if request.minimum_severity is not None:
        severities = dict(record.minimum_severity_json)
        for category, severity in request.minimum_severity.items():
            severities[category] = severity
        record.minimum_severity_json = severities
    if request.supplied("quiet_hours_start"):
        record.quiet_hours_start = request.quiet_hours_start
    if request.supplied("quiet_hours_end"):
        record.quiet_hours_end = request.quiet_hours_end
    if request.daily_digest_enabled is not None:
        record.daily_digest_enabled = request.daily_digest_enabled
    record.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(record)
    return preference_response(record)


def list_notifications(db: Session, user_id: str, *, limit: int, cursor: str | None = None) -> tuple[list[NotificationModel], str | None]:
    now = datetime.now(UTC)
    statement = (
        select(NotificationModel)
        .where(*_visible_notification_filters(user_id, now))
        .order_by(NotificationModel.created_at.desc(), NotificationModel.id.desc())
        .limit(limit + 1)
    )
    if cursor:
        cursor_created_at, cursor_id = _parse_cursor(cursor)
        statement = statement.where(
            or_(
                NotificationModel.created_at < cursor_created_at,
                and_(NotificationModel.created_at == cursor_created_at, NotificationModel.id < cursor_id),
            )
        )
    rows = db.execute(statement).scalars().all()
    page = rows[:limit]
    next_cursor = _encode_cursor(page[-1]) if len(rows) > limit and page else None
    return page, next_cursor


def unread_count(db: Session, user_id: str) -> int:
    now = datetime.now(UTC)
    return int(
        db.execute(
            select(func.count())
            .select_from(NotificationModel)
            .where(*_visible_notification_filters(user_id, now))
            .where(NotificationModel.read_at.is_(None))
        ).scalar_one()
        or 0
    )


def get_notification(db: Session, user_id: str, notification_id: str) -> NotificationModel:
    record = db.execute(
        select(NotificationModel)
        .where(NotificationModel.id == notification_id, *_visible_notification_filters(user_id, datetime.now(UTC)))
    ).scalars().one_or_none()
    if record is None:
        raise HTTPException(status_code=404, detail="Notification not found")
    return record


def mark_notification(db: Session, user_id: str, notification_id: str, *, read: bool) -> NotificationModel:
    record = get_notification(db, user_id, notification_id)
    now = datetime.now(UTC)
    record.read_at = now if read else None
    record.updated_at = now
    db.commit()
    db.refresh(record)
    return record


def mark_all_read(db: Session, user_id: str, *, limit: int) -> int:
    now = datetime.now(UTC)
    rows = db.execute(
        select(NotificationModel)
        .where(*_visible_notification_filters(user_id, now))
        .where(NotificationModel.read_at.is_(None))
        .order_by(NotificationModel.created_at.desc(), NotificationModel.id.desc())
        .limit(limit)
    ).scalars().all()
    for row in rows:
        row.read_at = now
        row.updated_at = now
    db.commit()
    return len(rows)


def notification_response(record: NotificationModel) -> NotificationResponse:
    return NotificationResponse(
        id=record.id,
        category=record.category,
        severity=record.severity,
        title=record.title,
        body=record.body,
        source_type=record.source_type,
        source_id=record.source_id,
        navigation=record.navigation_json,
        policy_outcome=record.policy_outcome,
        available_at=record.available_at,
        read_at=record.read_at,
        created_at=record.created_at,
        expires_at=record.expires_at,
    )


def cleanup_expired_notifications(db: Session, *, now: datetime | None = None, apply: bool = False) -> int:
    timestamp = now or datetime.now(UTC)
    statement = select(NotificationModel).where(NotificationModel.expires_at <= timestamp)
    rows = db.execute(statement).scalars().all()
    if apply and rows:
        db.execute(delete(NotificationModel).where(NotificationModel.id.in_([row.id for row in rows])))
        db.flush()
    return len(rows)


def dispose_notifications_for_account(db: Session, user_id: str) -> dict[str, int]:
    notification_count = len(db.execute(select(NotificationModel.id).where(NotificationModel.owner_user_id == user_id)).scalars().all())
    preference_count = len(db.execute(select(NotificationPreferenceModel.id).where(NotificationPreferenceModel.user_id == user_id)).scalars().all())
    db.execute(delete(NotificationModel).where(NotificationModel.owner_user_id == user_id))
    db.execute(delete(NotificationPreferenceModel).where(NotificationPreferenceModel.user_id == user_id))
    db.flush()
    return {"notifications": notification_count, "preferences": preference_count}


def _policy_outcome(preference: NotificationPreferenceModel, template: NotificationTemplate, now: datetime) -> tuple[str, datetime | None]:
    if template.category in MANDATORY_CATEGORIES:
        return "mandatory", now
    enabled = bool(preference.category_enabled_json.get(template.category, False))
    minimum = preference.minimum_severity_json.get(template.category, "informational")
    if not enabled or SEVERITY_RANK[template.severity] < SEVERITY_RANK.get(minimum, 0):
        return "suppressed_by_preference", None
    if preference.daily_digest_enabled:
        return "delayed_digest", _next_digest_at(preference, now)
    delayed = _quiet_hours_available_at(preference, now)
    if delayed is not None:
        return "delayed_quiet_hours", delayed
    return "available", now


def _quiet_hours_available_at(preference: NotificationPreferenceModel, now: datetime) -> datetime | None:
    if not preference.quiet_hours_start or not preference.quiet_hours_end:
        return None
    zone = ZoneInfo(preference.timezone)
    local_now = now.astimezone(zone)
    start = _parse_time(preference.quiet_hours_start)
    end = _parse_time(preference.quiet_hours_end)
    current = local_now.time().replace(second=0, microsecond=0)
    if start == end:
        return None
    in_quiet = current >= start or current < end if start > end else start <= current < end
    if not in_quiet:
        return None
    end_date = local_now.date()
    if start > end and current >= start:
        end_date += timedelta(days=1)
    return datetime.combine(end_date, end, tzinfo=zone).astimezone(UTC)


def _next_digest_at(preference: NotificationPreferenceModel, now: datetime) -> datetime:
    zone = ZoneInfo(preference.timezone)
    local_now = now.astimezone(zone)
    candidate = datetime.combine(local_now.date(), time(DEFAULT_DIGEST_HOUR, 0), tzinfo=zone)
    if candidate <= local_now:
        candidate += timedelta(days=1)
    quiet_end = _quiet_hours_available_at(preference, candidate.astimezone(UTC))
    return quiet_end or candidate.astimezone(UTC)


def _default_categories() -> dict[str, bool]:
    return {category: category in MANDATORY_CATEGORIES for category in CATEGORIES}


def _validate_timezone(value: str) -> None:
    try:
        ZoneInfo(value)
    except ZoneInfoNotFoundError as exc:
        raise HTTPException(status_code=422, detail="Timezone must be a valid IANA timezone.") from exc


def _parse_time(value: str) -> time:
    hour, minute = value.split(":", 1)
    return time(int(hour), int(minute))


def _visible_notification_filters(user_id: str, now: datetime) -> tuple:
    """The one visibility contract shared by inbox list, count, and mutations."""

    return (
        NotificationModel.owner_user_id == user_id,
        NotificationModel.available_at.is_not(None),
        NotificationModel.available_at <= now,
        NotificationModel.expires_at > now,
    )


def _encode_cursor(record: NotificationModel) -> str:
    payload = json.dumps({"v": 1, "created_at": _utc(record.created_at).isoformat(), "id": record.id}, separators=(",", ":"))
    return base64.urlsafe_b64encode(payload.encode("utf-8")).decode("ascii").rstrip("=")


def _parse_cursor(value: str) -> tuple[datetime, str]:
    try:
        if len(value) > 512:
            raise ValueError
        padded = value + "=" * (-len(value) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded.encode("ascii")))
        created_at = payload["created_at"]
        notification_id = payload["id"]
        if payload.get("v") != 1 or not isinstance(created_at, str) or not isinstance(notification_id, str) or not notification_id or len(notification_id) > 64:
            raise ValueError
        return _utc(datetime.fromisoformat(created_at)), notification_id
    except (KeyError, TypeError, ValueError, UnicodeDecodeError, binascii.Error, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=422, detail="Invalid notification cursor.") from exc


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
