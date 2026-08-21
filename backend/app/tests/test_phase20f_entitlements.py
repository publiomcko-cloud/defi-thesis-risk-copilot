from datetime import UTC, datetime

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.service import create_user
from app.db.base import Base
from app.entitlements.service import FREE_LIMITS, emit_usage, resolve_entitlements, reverse_usage
from app.models.entitlement import PlanEntitlementModel, PlanVersionModel, UsageEventModel


def test_server_resolver_is_read_only_and_usage_is_append_only() -> None:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    with Session() as db:
        user = create_user(db, "phase20f-owner@example.test")
        plan = PlanVersionModel(id="plan_free_v1", plan_key="free-v1", version=1, status="active", effective_from=datetime(2026, 8, 21, tzinfo=UTC))
        db.add(plan)
        db.add_all([PlanEntitlementModel(id=f"ent_{key.replace('.', '_')}", plan_version_id=plan.id, entitlement_key=key, hard_limit=value) for key, value in FREE_LIMITS.items()])
        db.commit()
        resolved = resolve_entitlements(db, user.id, now=datetime.now(UTC))
        assert resolved["plan"] == "free-v1"
        assert resolved["limits"] == FREE_LIMITS
        assert resolved["shadow"] == "parity"
        assert resolved["provenance"] == "implicit_server_default"
        first = emit_usage(db, owner_user_id=user.id, unit_key="usage.analysis.completed.v1", source_type="job", source_id="job_phase20f")
        duplicate = emit_usage(db, owner_user_id=user.id, unit_key="usage.analysis.completed.v1", source_type="job", source_id="job_phase20f")
        assert first is not None and duplicate is not None and first.id == duplicate.id
        reversal = reverse_usage(db, event_id=first.id, correction_code="operator_test_cleanup")
        assert reversal.quantity == -1 and reversal.reverses_event_id == first.id
        assert reverse_usage(db, event_id=first.id, correction_code="operator_test_cleanup").id == reversal.id
        db.commit()
        assert len(db.execute(select(UsageEventModel)).scalars().all()) == 2
