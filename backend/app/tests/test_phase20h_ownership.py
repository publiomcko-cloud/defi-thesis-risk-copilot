from __future__ import annotations

import time
from datetime import UTC, datetime, timedelta

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.dependencies import require_user
from app.auth.service import create_user, user_context
from app.auth.supabase import SupabaseClaims
from app.core.config import get_settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.access_audit_event import AccessAuditEventModel
from app.models.entitlement import PlanEntitlementModel, PlanVersionModel
from app.models.organization import OrganizationMembershipModel, OrganizationModel
from app.models.user import UserModel
from app.organizations.schemas import (
    InvitationCreateRequest,
    MembershipUpdateRequest,
    OrganizationUpdateRequest,
    OwnershipTransferRequest,
)
from app.organizations.service import (
    create_invitation,
    delete_organization,
    transfer_organization_ownership,
    update_member,
    update_organization,
)


@pytest.fixture
def ownership():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine)
    with sessions() as db:
        owner = create_user(db, "ownership-owner@example.test")
        admin = create_user(db, "ownership-admin@example.test")
        member = create_user(db, "ownership-member@example.test")
        viewer = create_user(db, "ownership-viewer@example.test")
        target = create_user(db, "ownership-target@example.test")
        pending = create_user(db, "ownership-pending@example.test")
        extra_owner = create_user(db, "ownership-extra-owner@example.test")
        platform_admin = create_user(db, "ownership-platform-admin@example.test", role="admin")
        outsider = create_user(db, "ownership-outsider@example.test")
        org = OrganizationModel(
            id="org_ownership",
            name="Ownership",
            slug="ownership",
            status="active",
            created_by_user_id=owner.id,
        )
        other_org = OrganizationModel(
            id="org_ownership_other",
            name="Other ownership",
            slug="ownership-other",
            status="active",
            created_by_user_id=outsider.id,
        )
        db.add_all([org, other_org])
        db.flush()
        db.add_all([
            OrganizationMembershipModel(id="mbr_owner", organization_id=org.id, user_id=owner.id, role="owner", status="active"),
            OrganizationMembershipModel(id="mbr_admin", organization_id=org.id, user_id=admin.id, role="admin", status="active"),
            OrganizationMembershipModel(id="mbr_member", organization_id=org.id, user_id=member.id, role="member", status="active"),
            OrganizationMembershipModel(id="mbr_viewer", organization_id=org.id, user_id=viewer.id, role="viewer", status="active"),
            OrganizationMembershipModel(id="mbr_target", organization_id=org.id, user_id=target.id, role="member", status="active"),
            OrganizationMembershipModel(id="mbr_pending", organization_id=org.id, user_id=pending.id, role="member", status="pending"),
            OrganizationMembershipModel(id="mbr_extra_owner", organization_id=org.id, user_id=extra_owner.id, role="owner", status="active"),
            OrganizationMembershipModel(id="mbr_other", organization_id=other_org.id, user_id=outsider.id, role="member", status="active"),
            PlanVersionModel(id="plan_portfolio_org_v1", plan_key="portfolio-org-v1", version=1, status="active", effective_from=datetime(2025, 8, 24, tzinfo=UTC)),
            PlanEntitlementModel(id="ent_portfolio_org_seats", plan_version_id="plan_portfolio_org_v1", entitlement_key="limit.organization.seats.count", hard_limit=10),
        ])
        db.commit()
        return sessions, {
            "owner": owner.id,
            "admin": admin.id,
            "member": member.id,
            "viewer": viewer.id,
            "target": target.id,
            "pending": pending.id,
            "extra_owner": extra_owner.id,
            "platform_admin": platform_admin.id,
            "outsider": outsider.id,
        }


def test_owner_and_admin_can_administer_but_only_owner_can_destroy_or_transfer(ownership):
    sessions, users = ownership
    with sessions() as db:
        owner = _actor(db, users["owner"])
        admin = _actor(db, users["admin"])
        platform_admin = _actor(db, users["platform_admin"])
        assert create_invitation(db, owner, "org_ownership", InvitationCreateRequest(email="owner-invite@example.test")).token
        assert create_invitation(db, admin, "org_ownership", InvitationCreateRequest(email="admin-invite@example.test")).token
        updated = update_member(db, admin, "org_ownership", "mbr_member", MembershipUpdateRequest(role="viewer"))
        assert updated.role == "viewer"

        for actor in (admin, platform_admin):
            with pytest.raises(HTTPException) as disabled:
                update_organization(db, actor, "org_ownership", OrganizationUpdateRequest(status="disabled"))
            assert disabled.value.status_code == 403
            with pytest.raises(HTTPException) as deleted:
                delete_organization(db, actor, "org_ownership")
            assert deleted.value.status_code == 403
            with pytest.raises(HTTPException) as transfer:
                transfer_organization_ownership(
                    db,
                    actor,
                    "org_ownership",
                    OwnershipTransferRequest(target_membership_id="mbr_target"),
                )
            assert transfer.value.status_code == 403


def test_lifecycle_owner_can_reactivate_and_delete_a_disabled_organization(ownership):
    sessions, users = ownership
    with sessions() as db:
        owner = _actor(db, users["owner"])
        admin = _actor(db, users["admin"])

        assert update_organization(
            db, owner, "org_ownership", OrganizationUpdateRequest(status="disabled")
        ).status == "disabled"
        with pytest.raises(HTTPException) as admin_reactivate:
            update_organization(db, admin, "org_ownership", OrganizationUpdateRequest(status="active"))
        assert admin_reactivate.value.status_code == 403

        assert update_organization(
            db, owner, "org_ownership", OrganizationUpdateRequest(status="active")
        ).status == "active"
        assert update_organization(
            db, owner, "org_ownership", OrganizationUpdateRequest(status="disabled")
        ).status == "disabled"
        assert delete_organization(db, owner, "org_ownership").status == "disabled"

        with pytest.raises(HTTPException) as deleted_reactivate:
            update_organization(db, owner, "org_ownership", OrganizationUpdateRequest(status="active"))
        assert deleted_reactivate.value.status_code == 404


def test_lifecycle_owner_can_delete_an_active_organization(ownership):
    sessions, users = ownership
    with sessions() as db:
        deleted = delete_organization(db, _actor(db, users["owner"]), "org_ownership")
        assert deleted.status == "disabled"
        assert db.get(OrganizationModel, "org_ownership").deleted_at is not None


def test_disabled_organization_keeps_lifecycle_authority_owner_only(ownership):
    sessions, users = ownership
    with sessions() as db:
        owner = _actor(db, users["owner"])
        platform_admin = _actor(db, users["platform_admin"])
        update_organization(db, owner, "org_ownership", OrganizationUpdateRequest(status="disabled"))

        with pytest.raises(HTTPException) as platform_delete:
            delete_organization(db, platform_admin, "org_ownership")
        assert platform_delete.value.status_code == 403

        with pytest.raises(HTTPException) as invite:
            create_invitation(
                db,
                owner,
                "org_ownership",
                InvitationCreateRequest(email="disabled-organization@example.test"),
            )
        assert invite.value.status_code == 403

        with pytest.raises(HTTPException) as transfer:
            transfer_organization_ownership(
                db,
                owner,
                "org_ownership",
                OwnershipTransferRequest(target_membership_id="mbr_target"),
            )
        assert transfer.value.status_code == 403


def test_members_and_viewers_cannot_administer_members(ownership):
    sessions, users = ownership
    with sessions() as db:
        for user_key in ("member", "viewer"):
            with pytest.raises(HTTPException) as error:
                update_member(
                    db,
                    _actor(db, users[user_key]),
                    "org_ownership",
                    "mbr_target",
                    MembershipUpdateRequest(role="viewer"),
                )
            assert error.value.status_code == 403


def test_generic_member_requests_cannot_create_or_mutate_owner_authority(ownership):
    sessions, users = ownership
    with sessions() as db:
        owner = _actor(db, users["owner"])
        with pytest.raises(ValidationError):
            MembershipUpdateRequest(role="owner")
        with pytest.raises(HTTPException, match="ownership transfer"):
            update_member(
                db,
                owner,
                "org_ownership",
                "mbr_target",
                MembershipUpdateRequest.model_construct(role="owner"),
            )
        for request in (
            MembershipUpdateRequest(role="admin"),
            MembershipUpdateRequest(status="removed"),
            MembershipUpdateRequest(status="pending"),
        ):
            with pytest.raises(HTTPException, match="ownership transfer"):
                update_member(db, owner, "org_ownership", "mbr_owner", request)


def test_transfer_promotes_active_same_org_member_and_preserves_unrelated_owners(ownership):
    sessions, users = ownership
    with sessions() as db:
        target = transfer_organization_ownership(
            db,
            _actor(db, users["owner"]),
            "org_ownership",
            OwnershipTransferRequest(target_membership_id="mbr_target"),
        )
        assert target.role == "owner"
        assert db.get(OrganizationMembershipModel, "mbr_owner").role == "admin"
        assert db.get(OrganizationMembershipModel, "mbr_target").role == "owner"
        assert db.get(OrganizationMembershipModel, "mbr_extra_owner").role == "owner"
        event = db.query(AccessAuditEventModel).filter_by(action="organization.ownership_transferred").one()
        assert event.metadata_json == {
            "from_membership_id": "mbr_owner",
            "from_user_id": users["owner"],
            "to_membership_id": "mbr_target",
            "to_user_id": users["target"],
            "from_role": "owner",
            "to_role": "owner",
        }


def test_transfer_rejects_self_pending_and_cross_organization_targets(ownership):
    sessions, users = ownership
    with sessions() as db:
        owner = _actor(db, users["owner"])
        for membership_id, expected_status in (("mbr_owner", 409), ("mbr_pending", 409), ("mbr_other", 404)):
            with pytest.raises(HTTPException) as error:
                transfer_organization_ownership(
                    db,
                    owner,
                    "org_ownership",
                    OwnershipTransferRequest(target_membership_id=membership_id),
                )
            assert error.value.status_code == expected_status


def test_recent_authentication_is_required_and_uses_only_context_evidence(ownership):
    sessions, users = ownership
    with sessions() as db:
        stale = _actor(db, users["owner"], authenticated_at=datetime.now(UTC) - timedelta(minutes=11))
        missing = _actor(db, users["owner"], authenticated_at=None)
        for actor in (stale, missing):
            with pytest.raises(HTTPException, match="Recent authentication") as error:
                transfer_organization_ownership(
                    db,
                    actor,
                    "org_ownership",
                    OwnershipTransferRequest(target_membership_id="mbr_target"),
                )
            assert error.value.status_code == 403


@pytest.fixture
def supabase_transfer_client(monkeypatch):
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("AUTH_PROVIDER", "supabase")
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("REQUIRE_VERIFIED_EMAIL", "true")
    monkeypatch.setenv("SUPABASE_URL", "https://project.supabase.co")
    monkeypatch.setenv("SUPABASE_JWKS_URL", "https://project.supabase.co/auth/v1/.well-known/jwks.json")
    monkeypatch.setenv("SUPABASE_JWT_ISSUER", "https://project.supabase.co/auth/v1")
    monkeypatch.setenv("BFF_AUDIT_SECRET", "phase20h-test-audit-secret")
    get_settings.cache_clear()
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine)
    with sessions() as db:
        owner = create_user(db, "supabase-owner@example.test")
        target = create_user(db, "supabase-target@example.test")
        owner.auth_provider, owner.auth_subject = "supabase", "supabase-owner"
        target.auth_provider, target.auth_subject = "supabase", "supabase-target"
        db.add(OrganizationModel(id="org_supabase", name="Supabase transfer", slug="supabase-transfer", status="active", created_by_user_id=owner.id))
        db.flush()
        db.add_all([
            OrganizationMembershipModel(id="mbr_supabase_owner", organization_id="org_supabase", user_id=owner.id, role="owner", status="active"),
            OrganizationMembershipModel(id="mbr_supabase_target", organization_id="org_supabase", user_id=target.id, role="member", status="active"),
        ])
        db.commit()

    def override_get_db():
        db = sessions()
        try:
            yield db
        finally:
            db.close()

    now = datetime.now(UTC)
    claims = {
        "fresh": _claims("supabase-owner", "supabase-owner@example.test", now),
        "stale": _claims("supabase-owner", "supabase-owner@example.test", now - timedelta(minutes=11)),
        "missing": _claims("supabase-owner", "supabase-owner@example.test", None),
        "aal-only": _claims("supabase-owner", "supabase-owner@example.test", None, aal="aal2"),
    }
    monkeypatch.setattr("app.auth.dependencies.verify_supabase_jwt", lambda token, _settings: claims[token])
    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()


def test_verified_supabase_auth_time_controls_transfer(supabase_transfer_client):
    response = supabase_transfer_client.post(
        "/api/organizations/org_supabase/transfer-ownership",
        json={"target_membership_id": "mbr_supabase_target"},
        headers=_auth("fresh"),
    )
    assert response.status_code == 200
    assert response.json()["role"] == "owner"


def test_api_lifecycle_owner_can_disable_and_reactivate_organization(supabase_transfer_client):
    disabled = supabase_transfer_client.patch(
        "/api/organizations/org_supabase",
        json={"status": "disabled"},
        headers=_auth("fresh"),
    )
    assert disabled.status_code == 200
    assert disabled.json()["status"] == "disabled"

    blocked_transfer = supabase_transfer_client.post(
        "/api/organizations/org_supabase/transfer-ownership",
        json={"target_membership_id": "mbr_supabase_target"},
        headers=_auth("fresh"),
    )
    assert blocked_transfer.status_code == 403

    reactivated = supabase_transfer_client.patch(
        "/api/organizations/org_supabase",
        json={"status": "active"},
        headers=_auth("fresh"),
    )
    assert reactivated.status_code == 200
    assert reactivated.json()["status"] == "active"


@pytest.mark.parametrize("token", ["stale", "missing", "aal-only"])
def test_stale_missing_or_mfa_only_provider_claims_cannot_transfer(supabase_transfer_client, token):
    response = supabase_transfer_client.post(
        "/api/organizations/org_supabase/transfer-ownership",
        json={"target_membership_id": "mbr_supabase_target"},
        headers=_auth(token),
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Recent authentication required"


def test_client_recency_fields_are_not_trusted(supabase_transfer_client):
    header = supabase_transfer_client.post(
        "/api/organizations/org_supabase/transfer-ownership",
        json={"target_membership_id": "mbr_supabase_target"},
        headers={**_auth("missing"), "X-Auth-Time": str(int(time.time()))},
    )
    forged_body = supabase_transfer_client.post(
        "/api/organizations/org_supabase/transfer-ownership",
        json={"target_membership_id": "mbr_supabase_target", "auth_time": int(time.time()), "recent": True},
        headers=_auth("missing"),
    )
    assert header.status_code == 403
    assert forged_body.status_code == 422


def test_legacy_recent_auth_is_explicitly_non_production_only(ownership, monkeypatch):
    sessions, users = ownership
    with sessions() as db:
        create_user(db, "local-recent-auth@example.test", token="local-recent-auth")
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="local-recent-auth")
        monkeypatch.setenv("AUTH_ENABLED", "true")
        monkeypatch.setenv("AUTH_PROVIDER", "legacy_local")
        monkeypatch.setenv("APP_ENV", "development")
        monkeypatch.setenv("OWNERSHIP_TRANSFER_LEGACY_LOCAL_RECENT_AUTH_ENABLED", "false")
        get_settings.cache_clear()
        assert require_user(credentials=credentials, db=db).authenticated_at is None

        monkeypatch.setenv("OWNERSHIP_TRANSFER_LEGACY_LOCAL_RECENT_AUTH_ENABLED", "true")
        get_settings.cache_clear()
        assert require_user(credentials=credentials, db=db).authenticated_at is not None

        monkeypatch.setenv("APP_ENV", "production")
        get_settings.cache_clear()
        with pytest.raises(ValidationError):
            require_user(credentials=credentials, db=db)
    get_settings.cache_clear()


_FRESH_AUTHENTICATION = object()


def _actor(db, user_id: str, authenticated_at: datetime | None | object = _FRESH_AUTHENTICATION):
    return user_context(
        db.get(UserModel, user_id),
        authenticated_at=datetime.now(UTC) if authenticated_at is _FRESH_AUTHENTICATION else authenticated_at,
    ).model_copy(update={"auth_provider": "supabase"})


def _claims(subject: str, email: str, authenticated_at: datetime | None, *, aal: str | None = None) -> SupabaseClaims:
    raw = {"auth_time": int(authenticated_at.timestamp())} if authenticated_at is not None else {}
    if aal is not None:
        raw["aal"] = aal
    return SupabaseClaims(
        subject=subject,
        email=email,
        email_verified=True,
        issuer="https://project.supabase.co/auth/v1",
        audience="authenticated",
        expires_at=int(time.time()) + 300,
        raw=raw,
        authenticated_at=authenticated_at,
    )


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}
