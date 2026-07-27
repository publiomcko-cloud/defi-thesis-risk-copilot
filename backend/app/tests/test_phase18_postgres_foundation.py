from __future__ import annotations

import os
from uuid import uuid4

import pytest
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.auth.service import create_user, user_context
from app.db.session import create_database_engine
from app.knowledge.access import (
    create_knowledge_source,
    get_visible_knowledge_source,
    list_visible_knowledge_sources,
)
from app.models.knowledge import KnowledgeSourceModel
from app.models.organization import OrganizationMembershipModel, OrganizationModel
from app.models.user import UserModel


pytestmark = pytest.mark.postgres_integration


@pytest.fixture(scope="module")
def postgres_sessions() -> sessionmaker:
    if os.getenv("RUN_POSTGRES_INTEGRATION") != "true":
        pytest.skip("Phase 18 PostgreSQL tests require RUN_POSTGRES_INTEGRATION=true")
    engine = create_database_engine()
    if engine.dialect.name != "postgresql":
        pytest.skip("Phase 18 PostgreSQL tests require a PostgreSQL DATABASE_URL")
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


def test_postgres_knowledge_scope_constraints_and_organization_isolation(
    postgres_sessions: sessionmaker,
) -> None:
    suffix = uuid4().hex[:10]
    with postgres_sessions() as db:
        owner = create_user(db, f"phase18-pg-owner-{suffix}@example.test")
        member = create_user(db, f"phase18-pg-member-{suffix}@example.test")
        outsider = create_user(db, f"phase18-pg-outsider-{suffix}@example.test")
        organization = OrganizationModel(
            id=f"org_phase18_pg_{suffix}",
            name="Phase 18 PostgreSQL",
            slug=f"phase-18-pg-{suffix}",
            status="active",
            created_by_user_id=owner.id,
        )
        db.add(organization)
        db.flush()
        db.add_all(
            [
                OrganizationMembershipModel(
                    id=f"mbr_phase18_pg_owner_{suffix}",
                    organization_id=organization.id,
                    user_id=owner.id,
                    role="owner",
                    status="active",
                ),
                OrganizationMembershipModel(
                    id=f"mbr_phase18_pg_member_{suffix}",
                    organization_id=organization.id,
                    user_id=member.id,
                    role="viewer",
                    status="active",
                ),
            ]
        )
        db.commit()
        ids = {
            "owner": owner.id,
            "member": member.id,
            "outsider": outsider.id,
            "organization": organization.id,
        }

    try:
        with postgres_sessions() as db:
            owner = db.get(UserModel, ids["owner"])
            member = db.get(UserModel, ids["member"])
            outsider = db.get(UserModel, ids["outsider"])
            source = create_knowledge_source(
                db,
                user_context(owner),
                visibility="organization",
                organization_id=ids["organization"],
                title="PostgreSQL tenant source",
                source_type="upload",
            )
            db.commit()
            source_id = source.id

            assert get_visible_knowledge_source(
                db,
                user_context(member),
                source_id,
            ).id == source_id
            assert list_visible_knowledge_sources(db, user_context(outsider)) == []

            invalid = KnowledgeSourceModel(
                id=f"ksrc_invalid_{suffix}",
                owner_user_id=ids["owner"],
                organization_id=ids["organization"],
                visibility="private",
                source_type="upload",
                title="Invalid mixed tenant scope",
                status="registered",
                trust_state="needs_review",
                created_by_user_id=ids["owner"],
            )
            db.add(invalid)
            with pytest.raises(IntegrityError) as constraint_error:
                db.flush()
            assert "ck_knowledge_sources_scope" in str(constraint_error.value)
            db.rollback()

            membership = db.execute(
                select(OrganizationMembershipModel)
                .where(
                    OrganizationMembershipModel.organization_id == ids["organization"]
                )
                .where(OrganizationMembershipModel.user_id == ids["member"])
            ).scalars().one()
            membership.status = "removed"
            db.commit()
            assert list_visible_knowledge_sources(db, user_context(member)) == []
    finally:
        with postgres_sessions() as db:
            db.execute(
                delete(KnowledgeSourceModel).where(
                    KnowledgeSourceModel.organization_id == ids["organization"]
                )
            )
            db.execute(
                delete(OrganizationMembershipModel).where(
                    OrganizationMembershipModel.organization_id == ids["organization"]
                )
            )
            db.execute(
                delete(OrganizationModel).where(
                    OrganizationModel.id == ids["organization"]
                )
            )
            db.execute(
                delete(UserModel).where(
                    UserModel.id.in_(
                        {ids["owner"], ids["member"], ids["outsider"]}
                    )
                )
            )
            db.commit()
