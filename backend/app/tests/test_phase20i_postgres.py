from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from threading import Barrier
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import delete, func, select
from sqlalchemy.orm import sessionmaker

from app.auth.service import create_user, user_context
from app.customer_requests.schemas import CustomerRequestCreateRequest
from app.customer_requests.service import close_customer_request, create_customer_request
from app.db.session import create_database_engine
from app.models.access_audit_event import AccessAuditEventModel
from app.models.customer_request import CustomerRequestModel
from app.models.user import UserModel


pytestmark = pytest.mark.postgres_integration


@pytest.fixture(scope="module")
def postgres_sessions() -> sessionmaker:
    if os.getenv("RUN_POSTGRES_INTEGRATION") != "true":
        pytest.skip("Phase 20I PostgreSQL tests require RUN_POSTGRES_INTEGRATION=true")
    engine = create_database_engine()
    if engine.dialect.name != "postgresql":
        pytest.skip("Phase 20I PostgreSQL tests require a PostgreSQL DATABASE_URL")
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


def test_postgres_concurrent_close_is_serialized_and_owner_scoped(postgres_sessions: sessionmaker) -> None:
    suffix = uuid4().hex[:12]
    owner_id = other_id = request_id = ""
    try:
        with postgres_sessions() as db:
            owner = create_user(db, f"phase20i-owner-{suffix}@example.test")
            other = create_user(db, f"phase20i-other-{suffix}@example.test")
            owner_id, other_id = owner.id, other.id
            request = create_customer_request(
                db,
                user_context(owner),
                CustomerRequestCreateRequest(
                    request_type="privacy_access_export",
                    subject="PostgreSQL close race",
                    description="The close path is serialized by a row lock.",
                ),
            )
            request_id = request.id

        barrier = Barrier(2)

        def close() -> tuple[str, str]:
            with postgres_sessions() as db:
                actor = user_context(db.get(UserModel, owner_id))
                barrier.wait(timeout=10)
                return "closed", close_customer_request(db, actor, request_id).workflow_state

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(lambda _: close(), range(2)))
        assert results == [("closed", "closed"), ("closed", "closed")]
        with postgres_sessions() as db:
            record = db.get(CustomerRequestModel, request_id)
            assert record is not None
            assert record.workflow_state == "closed"
            assert record.closed_at is not None and record.resolution_code == "requester_closed"
            assert db.scalar(
                select(func.count()).select_from(AccessAuditEventModel).where(
                    AccessAuditEventModel.action == "customer_request.closed",
                    AccessAuditEventModel.resource_id == request_id,
                )
            ) == 1
            with pytest.raises(HTTPException) as hidden:
                close_customer_request(db, user_context(db.get(UserModel, other_id)), request_id)
            assert hidden.value.status_code == 404
            db.rollback()
    finally:
        with postgres_sessions() as db:
            if request_id:
                db.execute(delete(AccessAuditEventModel).where(AccessAuditEventModel.resource_id == request_id))
                db.execute(delete(CustomerRequestModel).where(CustomerRequestModel.id == request_id))
            if owner_id or other_id:
                db.execute(delete(UserModel).where(UserModel.id.in_([item for item in (owner_id, other_id) if item])))
            db.commit()
