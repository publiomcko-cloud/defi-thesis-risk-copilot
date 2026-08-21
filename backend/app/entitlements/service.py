from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.entitlement import EntitlementAssignmentModel, PlanEntitlementModel, PlanVersionModel, UsageEventModel
from app.models.user import UserModel

FREE_PLAN_ID = "plan_free_v1"
DEFAULT_EFFECTIVE_FROM = datetime(2026, 8, 21, tzinfo=UTC)
FREE_LIMITS = {"analysis.daily": 25, "simulation.daily": 100, "options.daily": 100, "market_data.daily": 100, "saved_theses.active": 50, "watchlists.active": 25, "schedules.active": 5}
USAGE_UNITS = frozenset({"usage.analysis.completed.v1", "usage.simulation.completed.v1", "usage.options.completed.v1", "usage.schedule.run_completed.v1"})

def ensure_catalog(db: Session) -> PlanVersionModel:
    plan = db.get(PlanVersionModel, FREE_PLAN_ID)
    if plan is None:
        try:
            with db.begin_nested():
                plan = PlanVersionModel(id=FREE_PLAN_ID, plan_key="free-v1", version=1, status="active", effective_from=DEFAULT_EFFECTIVE_FROM)
                db.add(plan)
                for key, limit in FREE_LIMITS.items():
                    db.add(PlanEntitlementModel(id=f"ent_{key.replace('.', '_')}", plan_version_id=plan.id, entitlement_key=key, hard_limit=limit))
                db.flush()
        except IntegrityError:
            plan = db.get(PlanVersionModel, FREE_PLAN_ID)
    if plan is None:
        raise RuntimeError("The free-v1 entitlement catalog could not be initialized.")
    return plan

def _ensure_default_assignment(db: Session, user_id: str, plan: PlanVersionModel) -> EntitlementAssignmentModel | None:
    assignment = EntitlementAssignmentModel(id=f"assignment_{uuid4().hex[:12]}", subject_type="user", subject_id=user_id, plan_version_id=plan.id, effective_from=DEFAULT_EFFECTIVE_FROM, source="server_default")
    try:
        with db.begin_nested():
            db.add(assignment)
            db.flush()
        return assignment
    except IntegrityError:
        return db.execute(select(EntitlementAssignmentModel).where(EntitlementAssignmentModel.subject_type == "user", EntitlementAssignmentModel.subject_id == user_id, EntitlementAssignmentModel.plan_version_id == plan.id, EntitlementAssignmentModel.effective_from == DEFAULT_EFFECTIVE_FROM)).scalars().one_or_none()


def resolve_entitlements(db: Session, user_id: str, now: datetime | None = None) -> dict:
    now = now or datetime.now(UTC); plan = ensure_catalog(db)
    assignments = db.execute(select(EntitlementAssignmentModel).where(EntitlementAssignmentModel.subject_id == user_id).where(EntitlementAssignmentModel.effective_from <= now).where((EntitlementAssignmentModel.effective_until.is_(None)) | (EntitlementAssignmentModel.effective_until > now)).order_by(EntitlementAssignmentModel.effective_from.desc())).scalars().all()
    user = db.get(UserModel, user_id)
    if len(assignments) > 1: return {"plan": "free-v1", "version": 1, "provenance": "safe_fallback_ambiguous", "limits": dict(FREE_LIMITS), "shadow": "mismatch", "legacy_plan": user.plan if user else "unknown"}
    if assignments:
        assigned = db.get(PlanVersionModel, assignments[0].plan_version_id)
        if assigned is None or assigned.status != "active":
            return {"plan": "free-v1", "version": 1, "provenance": "safe_fallback_invalid", "limits": dict(FREE_LIMITS), "shadow": "mismatch", "legacy_plan": user.plan if user else "unknown"}
        plan = assigned; provenance = "assignment"
    else:
        _ensure_default_assignment(db, user_id, plan)
        provenance = "server_default"
    limits = {row.entitlement_key: row.hard_limit for row in db.execute(select(PlanEntitlementModel).where(PlanEntitlementModel.plan_version_id == plan.id)).scalars()}
    legacy_plan = user.plan if user is not None else "unknown"
    return {"plan": plan.plan_key, "version": plan.version, "provenance": provenance, "limits": limits or dict(FREE_LIMITS), "shadow": "parity" if legacy_plan == "free" else "mismatch", "legacy_plan": legacy_plan}

def emit_usage(db: Session, *, owner_user_id: str | None, unit_key: str, source_type: str, source_id: str) -> UsageEventModel | None:
    if owner_user_id is None or unit_key not in USAGE_UNITS: return None
    logical_key = f"{owner_user_id}:{source_type}:{source_id}"
    event = UsageEventModel(id=f"usage_{uuid4().hex[:12]}", owner_user_id=owner_user_id, unit_key=unit_key, quantity=1, logical_key=logical_key, source_type=source_type, source_id=source_id, occurred_at=datetime.now(UTC))
    try:
        with db.begin_nested(): db.add(event); db.flush()
    except IntegrityError:
        return db.execute(select(UsageEventModel).where(UsageEventModel.unit_key == unit_key, UsageEventModel.logical_key == logical_key)).scalars().one()
    return event


def reverse_usage(db: Session, *, event_id: str, correction_code: str) -> UsageEventModel:
    """Append one compensating entry; original usage rows are never edited."""

    original = db.get(UsageEventModel, event_id)
    if original is None:
        raise ValueError("Usage event does not exist.")
    reversal = UsageEventModel(
        id=f"usage_{uuid4().hex[:12]}", owner_user_id=original.owner_user_id,
        unit_key=original.unit_key, quantity=-original.quantity,
        logical_key=f"reversal:{original.id}", source_type="usage_reversal", source_id=original.id,
        occurred_at=datetime.now(UTC), reverses_event_id=original.id, correction_code=correction_code,
    )
    try:
        with db.begin_nested():
            db.add(reversal)
            db.flush()
    except IntegrityError:
        return db.execute(select(UsageEventModel).where(UsageEventModel.reverses_event_id == original.id)).scalars().one()
    return reversal

def dispose_entitlements_for_account(db: Session, user_id: str) -> None:
    db.execute(delete(UsageEventModel).where(UsageEventModel.owner_user_id == user_id)); db.execute(delete(EntitlementAssignmentModel).where(EntitlementAssignmentModel.subject_id == user_id)); db.flush()
