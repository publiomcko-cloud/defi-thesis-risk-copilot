from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.entitlement import EntitlementAssignmentModel, PlanEntitlementModel, PlanVersionModel, UsageEventModel
from app.models.user import UserModel
from app.scheduling.service import ACTIVE_SCHEDULE_LIMIT

logger = logging.getLogger(__name__)

FREE_PLAN_ID = "plan_free_v1"
FREE_LIMITS = {
    "limit.analysis.count": 25,
    "limit.simulation.count": 100,
    "limit.options.count": 100,
    "limit.market_data.count": 100,
    "limit.saved_thesis.count": 50,
    "limit.watchlist.count": 25,
    "limit.schedule.active_count": 5,
}
USAGE_UNITS = frozenset({"usage.analysis.completed.v1", "usage.simulation.completed.v1", "usage.options.completed.v1", "usage.schedule.run_completed.v1"})
CORRECTION_CODES = frozenset({"operator_duplicate", "operator_test_cleanup", "authoritative_outcome_voided"})


def _legacy_limits() -> dict[str, int]:
    settings = get_settings()
    return {
        "limit.analysis.count": settings.quota_free_analyses_per_day,
        "limit.simulation.count": settings.quota_free_simulations_per_day,
        "limit.options.count": settings.quota_free_options_per_day,
        "limit.market_data.count": settings.quota_free_market_data_per_day,
        "limit.saved_thesis.count": settings.quota_free_saved_theses,
        "limit.watchlist.count": settings.quota_free_watchlists,
        "limit.schedule.active_count": ACTIVE_SCHEDULE_LIMIT,
    }


def _safe_fallback(reason: str) -> dict:
    legacy = _legacy_limits()
    comparisons = [{"key": key, "result": "fallback", "legacy_limit": value, "entitlement_limit": None} for key, value in legacy.items()]
    logger.warning("entitlement_shadow_fallback reason=%s keys=%s", reason, ",".join(legacy))
    return {"plan": "legacy-authority", "version": None, "provenance": f"safe_fallback_{reason}", "limits": legacy, "shadow": "mismatch", "comparisons": comparisons}


def resolve_entitlements(db: Session, user_id: str, now: datetime | None = None) -> dict:
    """Read-only server-side shadow projection. It never authorizes admission."""

    timestamp = now or datetime.now(UTC)
    user = db.get(UserModel, user_id)
    if user is None or user.deleted_at is not None:
        return _safe_fallback("unknown_user")
    catalog = db.get(PlanVersionModel, FREE_PLAN_ID)
    if catalog is None or catalog.plan_key != "free-v1" or catalog.version != 1 or catalog.status != "active":
        return _safe_fallback("invalid_catalog")
    rows = db.execute(select(PlanEntitlementModel).where(PlanEntitlementModel.plan_version_id == catalog.id)).scalars().all()
    limits = {row.entitlement_key: row.hard_limit for row in rows}
    if set(limits) != set(FREE_LIMITS) or any(not isinstance(value, int) or value < 0 for value in limits.values()):
        return _safe_fallback("incomplete_catalog")
    assignments = db.execute(
        select(EntitlementAssignmentModel)
        .where(EntitlementAssignmentModel.subject_type == "user", EntitlementAssignmentModel.subject_id == user_id)
        .where(EntitlementAssignmentModel.effective_from <= timestamp)
        .where((EntitlementAssignmentModel.effective_until.is_(None)) | (EntitlementAssignmentModel.effective_until > timestamp))
        .order_by(EntitlementAssignmentModel.effective_from.desc())
    ).scalars().all()
    if len(assignments) > 1:
        return _safe_fallback("ambiguous_assignment")
    if assignments and assignments[0].plan_version_id != FREE_PLAN_ID:
        return _safe_fallback("invalid_assignment")
    legacy = _legacy_limits()
    comparisons = [
        {"key": key, "result": "parity" if limits[key] == legacy[key] else "mismatch", "legacy_limit": legacy[key], "entitlement_limit": limits[key]}
        for key in sorted(legacy)
    ]
    shadow = "parity" if all(item["result"] == "parity" for item in comparisons) else "mismatch"
    logger.info("entitlement_shadow_comparison result=%s comparisons=%s", shadow, comparisons)
    return {"plan": catalog.plan_key, "version": catalog.version, "provenance": "assignment" if assignments else "implicit_server_default", "limits": limits, "shadow": shadow, "comparisons": comparisons}


def emit_usage(db: Session, *, owner_user_id: str | None, unit_key: str, source_type: str, source_id: str) -> UsageEventModel | None:
    if owner_user_id is None or unit_key not in USAGE_UNITS:
        return None
    logical_key = f"{owner_user_id}:{source_type}:{source_id}"
    event = UsageEventModel(id=f"usage_{uuid4().hex[:12]}", owner_user_id=owner_user_id, unit_key=unit_key, quantity=1, logical_key=logical_key, source_type=source_type, source_id=source_id, occurred_at=datetime.now(UTC))
    try:
        with db.begin_nested():
            db.add(event); db.flush()
    except IntegrityError:
        return db.execute(select(UsageEventModel).where(UsageEventModel.unit_key == unit_key, UsageEventModel.logical_key == logical_key)).scalars().one()
    return event


def reverse_usage(db: Session, *, event_id: str, correction_code: str) -> UsageEventModel:
    """Append one registry-backed reversal; originals and quota counters stay untouched."""

    if correction_code not in CORRECTION_CODES:
        raise ValueError("Usage correction code is not approved.")
    original = db.get(UsageEventModel, event_id)
    if original is None or original.quantity <= 0 or original.reverses_event_id is not None:
        raise ValueError("Only an original positive usage event can be reversed.")
    reversal = UsageEventModel(id=f"usage_{uuid4().hex[:12]}", owner_user_id=original.owner_user_id, unit_key=original.unit_key, quantity=-original.quantity, logical_key=f"reversal:{original.id}", source_type="usage_reversal", source_id=original.id, occurred_at=datetime.now(UTC), reverses_event_id=original.id, correction_code=correction_code)
    try:
        with db.begin_nested():
            db.add(reversal); db.flush()
    except IntegrityError:
        return db.execute(select(UsageEventModel).where(UsageEventModel.reverses_event_id == original.id)).scalars().one()
    return reversal


def usage_counts(db: Session, user_id: str) -> dict[str, int]:
    rows = db.execute(select(UsageEventModel.unit_key, func.coalesce(func.sum(UsageEventModel.quantity), 0)).where(UsageEventModel.owner_user_id == user_id).group_by(UsageEventModel.unit_key)).all()
    counts = {key: 0 for key in USAGE_UNITS}
    counts.update({unit: int(quantity) for unit, quantity in rows})
    return counts


def dispose_entitlements_for_account(db: Session, user_id: str) -> None:
    db.execute(delete(UsageEventModel).where(UsageEventModel.owner_user_id == user_id))
    db.execute(delete(EntitlementAssignmentModel).where(EntitlementAssignmentModel.subject_id == user_id))
    db.flush()
