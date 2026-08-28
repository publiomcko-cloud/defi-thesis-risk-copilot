from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from threading import Barrier
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import delete, event, func, select
from sqlalchemy.orm import sessionmaker

from app.auth.service import create_user, user_context
from app.db.session import create_database_engine
from app.models.organization import OrganizationMembershipModel, OrganizationModel
from app.models.user import UserModel
from app.organizations.schemas import OwnershipTransferRequest
from app.organizations.service import remove_member, transfer_organization_ownership

pytestmark = pytest.mark.postgres_integration


@pytest.fixture(scope="module")
def postgres_sessions() -> sessionmaker:
    if os.getenv("RUN_POSTGRES_INTEGRATION") != "true":
        pytest.skip("Phase 20H PostgreSQL ownership tests require RUN_POSTGRES_INTEGRATION=true")
    engine = create_database_engine()
    if engine.dialect.name != "postgresql":
        pytest.skip("Phase 20H PostgreSQL ownership tests require a PostgreSQL DATABASE_URL")
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


def test_postgres_concurrent_ownership_transfer_has_one_authoritative_result(postgres_sessions: sessionmaker) -> None:
    suffix = uuid4().hex[:12]
    organization_id, owner_id, target_id, _ = _seed_organization(postgres_sessions, suffix)
    engine = postgres_sessions.kw["bind"]
    lock_barrier = Barrier(2)
    lock_selects = 0

    def synchronize_org_lock(connection, cursor, statement, parameters, context, executemany):
        nonlocal lock_selects
        if "FROM organizations" in statement and "FOR UPDATE" in statement:
            lock_selects += 1
            lock_barrier.wait(timeout=10)

    def transfer() -> tuple[str, int | str]:
        with postgres_sessions() as db:
            try:
                response = transfer_organization_ownership(
                    db,
                    _recent_actor(db, owner_id),
                    organization_id,
                    OwnershipTransferRequest(target_membership_id="mbr_target_" + suffix),
                )
                return "success", response.id
            except HTTPException as error:
                db.rollback()
                return "error", error.status_code

    event.listen(engine, "before_cursor_execute", synchronize_org_lock)
    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(lambda _: transfer(), range(2)))
        assert sorted(item[0] for item in results) == ["error", "success"]
        assert lock_selects == 2
        with postgres_sessions() as db:
            assert db.get(OrganizationMembershipModel, "mbr_owner_" + suffix).role == "admin"
            assert db.get(OrganizationMembershipModel, "mbr_target_" + suffix).role == "owner"
            assert _active_owner_count(db, organization_id) == 1
    finally:
        event.remove(engine, "before_cursor_execute", synchronize_org_lock)
        _cleanup_organization(postgres_sessions, organization_id)


def test_postgres_owner_removal_race_never_leaves_zero_active_owners(postgres_sessions: sessionmaker) -> None:
    suffix = uuid4().hex[:12]
    organization_id, owner_id, _, _ = _seed_organization(postgres_sessions, suffix)
    start = Barrier(2)

    def transfer() -> tuple[str, int | str]:
        with postgres_sessions() as db:
            try:
                start.wait(timeout=10)
                response = transfer_organization_ownership(
                    db,
                    _recent_actor(db, owner_id),
                    organization_id,
                    OwnershipTransferRequest(target_membership_id="mbr_target_" + suffix),
                )
                return "transfer", response.id
            except HTTPException as error:
                db.rollback()
                return "transfer_error", error.status_code

    def remove_owner() -> tuple[str, int | str]:
        with postgres_sessions() as db:
            try:
                start.wait(timeout=10)
                response = remove_member(
                    db,
                    _recent_actor(db, owner_id),
                    organization_id,
                    "mbr_owner_" + suffix,
                )
                return "remove", response.id
            except HTTPException as error:
                db.rollback()
                return "remove_error", error.status_code

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(lambda operation: operation(), [transfer, remove_owner]))
        assert any(item[0] == "transfer" for item in results)
        with postgres_sessions() as db:
            assert _active_owner_count(db, organization_id) >= 1
            assert db.get(OrganizationMembershipModel, "mbr_target_" + suffix).role == "owner"
    finally:
        _cleanup_organization(postgres_sessions, organization_id)


def test_postgres_transfer_preserves_unrelated_legacy_owner(postgres_sessions: sessionmaker) -> None:
    suffix = uuid4().hex[:12]
    organization_id, owner_id, _, extra_owner_id = _seed_organization(
        postgres_sessions,
        suffix,
        include_extra_owner=True,
    )
    try:
        with postgres_sessions() as db:
            assert extra_owner_id is not None
            transfer_organization_ownership(
                db,
                _recent_actor(db, owner_id),
                organization_id,
                OwnershipTransferRequest(target_membership_id="mbr_target_" + suffix),
            )
            assert db.get(OrganizationMembershipModel, "mbr_owner_" + suffix).role == "admin"
            assert db.get(OrganizationMembershipModel, "mbr_target_" + suffix).role == "owner"
            extra = db.get(OrganizationMembershipModel, "mbr_extra_owner_" + suffix)
            assert extra.user_id == extra_owner_id and extra.role == "owner"
            assert _active_owner_count(db, organization_id) == 2
    finally:
        _cleanup_organization(postgres_sessions, organization_id)


def _seed_organization(
    sessions: sessionmaker,
    suffix: str,
    *,
    include_extra_owner: bool = False,
) -> tuple[str, str, str, str | None]:
    with sessions() as db:
        owner = create_user(db, f"phase20h-transfer-owner-{suffix}@example.test")
        target = create_user(db, f"phase20h-transfer-target-{suffix}@example.test")
        extra_owner = create_user(db, f"phase20h-transfer-extra-{suffix}@example.test") if include_extra_owner else None
        organization_id = "org_transfer_" + suffix
        db.add(
            OrganizationModel(
                id=organization_id,
                name="Phase 20H transfer " + suffix,
                slug="phase20h-transfer-" + suffix,
                status="active",
                created_by_user_id=owner.id,
            )
        )
        db.flush()
        memberships = [
            OrganizationMembershipModel(id="mbr_owner_" + suffix, organization_id=organization_id, user_id=owner.id, role="owner", status="active"),
            OrganizationMembershipModel(id="mbr_target_" + suffix, organization_id=organization_id, user_id=target.id, role="member", status="active"),
        ]
        if extra_owner is not None:
            memberships.append(
                OrganizationMembershipModel(id="mbr_extra_owner_" + suffix, organization_id=organization_id, user_id=extra_owner.id, role="owner", status="active")
            )
        db.add_all(memberships)
        db.commit()
        return organization_id, owner.id, target.id, extra_owner.id if extra_owner is not None else None


def _recent_actor(db, user_id: str):
    return user_context(
        db.get(UserModel, user_id),
        authenticated_at=datetime.now(UTC),
    ).model_copy(update={"auth_provider": "supabase"})


def _active_owner_count(db, organization_id: str) -> int:
    return db.scalar(
        select(func.count())
        .select_from(OrganizationMembershipModel)
        .where(OrganizationMembershipModel.organization_id == organization_id)
        .where(OrganizationMembershipModel.role == "owner")
        .where(OrganizationMembershipModel.status == "active")
    ) or 0


def _cleanup_organization(sessions: sessionmaker, organization_id: str) -> None:
    with sessions() as db:
        user_ids = list(
            db.scalars(
                select(OrganizationMembershipModel.user_id).where(
                    OrganizationMembershipModel.organization_id == organization_id
                )
            )
        )
        db.execute(delete(OrganizationMembershipModel).where(OrganizationMembershipModel.organization_id == organization_id))
        db.execute(delete(OrganizationModel).where(OrganizationModel.id == organization_id))
        if user_ids:
            db.execute(delete(UserModel).where(UserModel.id.in_(user_ids)))
        db.commit()
