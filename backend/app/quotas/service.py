from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.schemas import UserContext
from app.core.config import get_settings
from app.models.usage_quota import UsageQuotaModel
from app.models.saved_thesis import SavedThesisModel
from app.models.watchlist_item import WatchlistItemModel


ACTION_ANALYSIS = "analysis"
ACTION_SIMULATION = "simulation"
ACTION_OPTIONS = "options_analysis"
ACTION_MARKET_DATA = "market_data_fetch"
RESOURCE_SAVED_THESES = "saved_theses"
RESOURCE_WATCHLISTS = "watchlists"


def consume_quota(
    db: Session,
    actor: UserContext,
    action: str,
    amount: int = 1,
) -> dict:
    settings = get_settings()
    if actor.is_admin and settings.quota_admin_exempt:
        return {"limited": False, "remaining": None, "limit": None, "used": None}

    subject_type = "anonymous" if actor.anonymous_session_id else "user"
    subject_id = actor.anonymous_session_id or actor.id
    plan = "anonymous" if subject_type == "anonymous" else actor.plan
    limit = _limit_for(plan, action)
    if limit is None:
        return {"limited": False, "remaining": None, "limit": None, "used": None}

    period_start, period_end = _day_window()
    now = datetime.now(UTC)
    record = _get_or_create_quota_record(
        db,
        subject_type=subject_type,
        subject_id=subject_id,
        plan=plan,
        action=action,
        period_start=period_start,
        period_end=period_end,
        limit=limit,
        now=now,
    )
    if record.used + amount > record.limit:
        raise HTTPException(
            status_code=429,
            detail=f"Daily {action} quota exceeded.",
            headers={"X-Quota-Limit": str(record.limit), "X-Quota-Remaining": "0"},
        )
    record.used += amount
    record.updated_at = now
    db.commit()
    return {
        "limited": True,
        "remaining": max(record.limit - record.used, 0),
        "limit": record.limit,
        "used": record.used,
        "period_end": record.period_end.isoformat(),
    }


def usage_summary(db: Session, actor: UserContext) -> dict:
    subject_type = "anonymous" if actor.anonymous_session_id else "user"
    subject_id = actor.anonymous_session_id or actor.id
    records = db.execute(
        select(UsageQuotaModel)
        .where(UsageQuotaModel.subject_type == subject_type)
        .where(UsageQuotaModel.subject_id == subject_id)
        .order_by(UsageQuotaModel.period_start.desc())
    ).scalars().all()
    return {
        "subject_type": subject_type,
        "items": [
            {
                "action": record.action,
                "used": record.used,
                "limit": record.limit,
                "remaining": max(record.limit - record.used, 0),
                "period_start": record.period_start,
                "period_end": record.period_end,
            }
            for record in records
        ],
    }


def enforce_resource_count_limit(db: Session, actor: UserContext, resource: str) -> None:
    settings = get_settings()
    if actor.is_admin and settings.quota_admin_exempt:
        return
    if actor.anonymous_session_id:
        raise HTTPException(status_code=403, detail=f"Anonymous users cannot create {resource}.")
    if resource == RESOURCE_SAVED_THESES:
        limit = settings.quota_free_saved_theses
        model = SavedThesisModel
    elif resource == RESOURCE_WATCHLISTS:
        limit = settings.quota_free_watchlists
        model = WatchlistItemModel
    else:
        return
    _get_or_create_quota_record(
        db,
        subject_type="user",
        subject_id=actor.id,
        plan=actor.plan,
        action=f"resource_count:{resource}",
        period_start=datetime(1970, 1, 1, tzinfo=UTC),
        period_end=datetime(9999, 12, 31, tzinfo=UTC),
        limit=limit,
        now=datetime.now(UTC),
    )
    count = len(
        db.execute(
            select(model)
            .where(model.owner_user_id == actor.id)
            .where(model.deleted_at.is_(None))
        ).scalars().all()
    )
    if count >= limit:
        raise HTTPException(status_code=429, detail=f"{resource} quota exceeded.")


def _limit_for(plan: str, action: str) -> int | None:
    settings = get_settings()
    if plan == "admin":
        return None
    if plan == "anonymous":
        if action == ACTION_ANALYSIS:
            return settings.quota_anonymous_analyses_per_day
        return 25
    mapping = {
        ACTION_ANALYSIS: settings.quota_free_analyses_per_day,
        ACTION_SIMULATION: settings.quota_free_simulations_per_day,
        ACTION_OPTIONS: settings.quota_free_options_per_day,
        ACTION_MARKET_DATA: settings.quota_free_market_data_per_day,
    }
    return mapping.get(action)


def _day_window() -> tuple[datetime, datetime]:
    now = datetime.now(UTC)
    start = datetime(now.year, now.month, now.day, tzinfo=UTC)
    return start, start + timedelta(days=1)


def _get_or_create_quota_record(
    db: Session,
    *,
    subject_type: str,
    subject_id: str,
    plan: str,
    action: str,
    period_start: datetime,
    period_end: datetime,
    limit: int,
    now: datetime,
) -> UsageQuotaModel:
    for _ in range(2):
        record = db.execute(
            select(UsageQuotaModel)
            .where(UsageQuotaModel.subject_type == subject_type)
            .where(UsageQuotaModel.subject_id == subject_id)
            .where(UsageQuotaModel.action == action)
            .where(UsageQuotaModel.period_start == period_start)
            .where(UsageQuotaModel.period_end == period_end)
            .with_for_update()
        ).scalars().first()
        if record is not None:
            return record
        record = UsageQuotaModel(
            id=f"quota_{uuid4().hex[:12]}",
            subject_type=subject_type,
            subject_id=subject_id,
            plan=plan,
            action=action,
            period_start=period_start,
            period_end=period_end,
            used=0,
            limit=limit,
            created_at=now,
            updated_at=now,
        )
        db.add(record)
        try:
            db.flush()
            return record
        except IntegrityError:
            db.rollback()
    record = db.execute(
        select(UsageQuotaModel)
        .where(UsageQuotaModel.subject_type == subject_type)
        .where(UsageQuotaModel.subject_id == subject_id)
        .where(UsageQuotaModel.action == action)
        .where(UsageQuotaModel.period_start == period_start)
        .where(UsageQuotaModel.period_end == period_end)
        .with_for_update()
    ).scalars().first()
    if record is None:
        raise HTTPException(status_code=409, detail="Quota record could not be initialized. Retry the request.")
    return record
