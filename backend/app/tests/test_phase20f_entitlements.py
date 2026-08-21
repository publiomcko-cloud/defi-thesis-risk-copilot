from datetime import UTC, datetime

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.service import create_user
from app.db.base import Base
from app.entitlements.service import FREE_LIMITS, emit_usage, resolve_entitlements, reverse_usage
from app.models.entitlement import EntitlementAssignmentModel, UsageEventModel


def test_server_resolver_initializes_one_free_assignment_and_usage_is_append_only() -> None:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    with Session() as db:
        user = create_user(db, "phase20f-owner@example.test")
        db.commit()
        resolved = resolve_entitlements(db, user.id, now=datetime.now(UTC))
        assert resolved["plan"] == "free-v1"
        assert resolved["limits"] == FREE_LIMITS
        assert resolved["shadow"] == "parity"
        assert len(db.execute(select(EntitlementAssignmentModel).where(EntitlementAssignmentModel.subject_id == user.id)).scalars().all()) == 1
        first = emit_usage(db, owner_user_id=user.id, unit_key="usage.analysis.completed.v1", source_type="job", source_id="job_phase20f")
        duplicate = emit_usage(db, owner_user_id=user.id, unit_key="usage.analysis.completed.v1", source_type="job", source_id="job_phase20f")
        assert first is not None and duplicate is not None and first.id == duplicate.id
        reversal = reverse_usage(db, event_id=first.id, correction_code="operator_correction")
        assert reversal.quantity == -1 and reversal.reverses_event_id == first.id
        assert reverse_usage(db, event_id=first.id, correction_code="operator_correction").id == reversal.id
        db.commit()
        assert len(db.execute(select(UsageEventModel)).scalars().all()) == 2
