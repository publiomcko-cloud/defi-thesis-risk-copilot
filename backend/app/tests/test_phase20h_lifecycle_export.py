from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.service import create_user
from app.core.config import get_settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.access_audit_event import AccessAuditEventModel
from app.models.entitlement import PlanEntitlementModel, PlanVersionModel
from app.models.organization import OrganizationInvitationModel, OrganizationMembershipModel, OrganizationModel
from app.models.user import UserModel
from app.organizations.service import seat_status


@pytest.fixture
def lifecycle_export_client(monkeypatch):
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("AUTH_PROVIDER", "legacy_local")
    monkeypatch.setenv("AUTH_SECRET_KEY", "phase20h-lifecycle-export-secret")
    monkeypatch.setenv("BFF_AUDIT_SECRET", "phase20h-lifecycle-export-audit")
    monkeypatch.setenv("APP_ENV", "development")
    get_settings.cache_clear()
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    with Session() as db:
        owner = create_user(db, "lifecycle-owner@example.test", token="lifecycle-owner-token")
        admin = create_user(db, "lifecycle-admin@example.test", token="lifecycle-admin-token")
        member = create_user(db, "lifecycle-member@example.test", token="lifecycle-member-token")
        viewer = create_user(db, "lifecycle-viewer@example.test", token="lifecycle-viewer-token")
        recipient = create_user(db, "lifecycle-recipient@example.test", token="lifecycle-recipient-token")
        account_target = create_user(db, "account-target@example.test", token="account-target-token")
        other_owner = create_user(db, "other-owner@example.test", token="other-owner-token")
        outsider = create_user(db, "lifecycle-outsider@example.test", token="lifecycle-outsider-token")
        platform_admin = create_user(
            db,
            "lifecycle-platform-admin@example.test",
            role="admin",
            token="lifecycle-platform-admin-token",
        )
        primary = OrganizationModel(
            id="org_lifecycle_export",
            name="Lifecycle Export",
            slug="lifecycle-export",
            status="active",
            created_by_user_id=owner.id,
        )
        other = OrganizationModel(
            id="org_lifecycle_export_other",
            name="Other Lifecycle Export",
            slug="other-lifecycle-export",
            status="active",
            created_by_user_id=other_owner.id,
        )
        db.add_all([primary, other])
        db.flush()
        db.add_all([
            OrganizationMembershipModel(
                id="mbr_lifecycle_owner",
                organization_id=primary.id,
                user_id=owner.id,
                role="owner",
                status="active",
            ),
            OrganizationMembershipModel(
                id="mbr_lifecycle_admin",
                organization_id=primary.id,
                user_id=admin.id,
                role="admin",
                status="active",
            ),
            OrganizationMembershipModel(
                id="mbr_lifecycle_member",
                organization_id=primary.id,
                user_id=member.id,
                role="member",
                status="active",
            ),
            OrganizationMembershipModel(
                id="mbr_lifecycle_viewer",
                organization_id=primary.id,
                user_id=viewer.id,
                role="viewer",
                status="active",
            ),
            OrganizationMembershipModel(
                id="mbr_lifecycle_other_owner",
                organization_id=other.id,
                user_id=other_owner.id,
                role="owner",
                status="active",
            ),
            PlanVersionModel(
                id="plan_portfolio_org_v1",
                plan_key="portfolio-org-v1",
                version=1,
                status="active",
                effective_from=datetime(2025, 8, 24, tzinfo=UTC),
            ),
            PlanEntitlementModel(
                id="ent_portfolio_org_seats",
                plan_version_id="plan_portfolio_org_v1",
                entitlement_key="limit.organization.seats.count",
                hard_limit=5,
            ),
        ])
        db.commit()
        identities = {
            "recipient_email": recipient.email,
            "account_target_id": account_target.id,
            "account_target_email": account_target.email,
        }

    def override_get_db():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app), Session, identities
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()


def test_organization_deletion_revokes_pending_invitations_and_preserves_other_tenants(lifecycle_export_client):
    client, Session, identities = lifecycle_export_client
    pending = _invite(client, "org_lifecycle_export", "lifecycle-owner-token", identities["recipient_email"])
    other_pending = _invite(
        client,
        "org_lifecycle_export_other",
        "other-owner-token",
        "other-tenant-recipient@example.test",
    )
    with Session() as db:
        assert seat_status(db, "org_lifecycle_export")["reserved"] == 1

    deleted = client.delete(
        "/api/organizations/org_lifecycle_export",
        headers=_auth("lifecycle-owner-token"),
    )
    assert deleted.status_code == 200
    assert deleted.json()["status"] == "disabled"

    rejected = client.post(
        "/api/organization-invitations/accept",
        json={"token": pending["token"]},
        headers=_auth("lifecycle-recipient-token"),
    )
    assert rejected.status_code == 409
    assert pending["token"] not in rejected.text
    resend_after_delete = client.post(
        f"/api/organizations/org_lifecycle_export/invitations/{pending['id']}/resend",
        headers=_auth("lifecycle-owner-token"),
    )
    revoke_after_delete = client.post(
        f"/api/organizations/org_lifecycle_export/invitations/{pending['id']}/revoke",
        headers=_auth("lifecycle-owner-token"),
    )
    for response in (resend_after_delete, revoke_after_delete):
        assert response.status_code == 404
        assert pending["token"] not in response.text
        assert "token_hash" not in response.text

    with Session() as db:
        invitation = db.get(OrganizationInvitationModel, pending["id"])
        assert invitation.status == "revoked"
        assert invitation.revoked_at is not None
        assert seat_status(db, "org_lifecycle_export")["reserved"] == 0
        assert db.get(OrganizationInvitationModel, other_pending["id"]).status == "pending"
        cleanup_event = db.execute(
            select(AccessAuditEventModel).where(
                AccessAuditEventModel.action == "organization.invitations_revoked"
            )
        ).scalars().one()
        assert cleanup_event.metadata_json == {"revoked_count": 1}


def test_account_deletion_revokes_only_addressed_pending_invitations(lifecycle_export_client):
    client, Session, identities = lifecycle_export_client
    addressed = _invite(
        client,
        "org_lifecycle_export",
        "lifecycle-owner-token",
        identities["account_target_email"],
    )
    unrelated = _invite(
        client,
        "org_lifecycle_export_other",
        "other-owner-token",
        "unrelated-account@example.test",
    )
    with Session() as db:
        assert seat_status(db, "org_lifecycle_export") == {
            "limit": 5,
            "active": 4,
            "reserved": 1,
            "consumed": 5,
            "remaining": 0,
        }

    deleted = client.request(
        "DELETE",
        "/api/account",
        json={"confirmation": "DELETE"},
        headers=_auth("account-target-token"),
    )
    assert deleted.status_code == 200

    with Session() as db:
        assert db.get(OrganizationInvitationModel, addressed["id"]).status == "revoked"
        assert db.get(OrganizationInvitationModel, unrelated["id"]).status == "pending"
        assert seat_status(db, "org_lifecycle_export") == {
            "limit": 5,
            "active": 4,
            "reserved": 0,
            "consumed": 4,
            "remaining": 1,
        }
        target = db.get(UserModel, identities["account_target_id"])
        assert target.account_status == "deleted"
        assert target.email == f"deleted-{target.id}@deleted.local"
        event = db.execute(
            select(AccessAuditEventModel).where(
                AccessAuditEventModel.action == "account.invitations_revoked"
            )
        ).scalars().one()
        assert event.metadata_json == {"revoked_count": 1}


def test_organization_export_has_safe_metadata_and_active_tenant_authorization(lifecycle_export_client):
    client, Session, _ = lifecycle_export_client
    pending = _invite(
        client,
        "org_lifecycle_export",
        "lifecycle-owner-token",
        "export-recipient@example.test",
    )

    owner_export = client.get(
        "/api/organizations/org_lifecycle_export/export",
        headers=_auth("lifecycle-owner-token"),
    )
    admin_export = client.get(
        "/api/organizations/org_lifecycle_export/export",
        headers=_auth("lifecycle-admin-token"),
    )
    assert owner_export.status_code == 200
    assert admin_export.status_code == 200
    payload = owner_export.json()
    assert set(payload["organization"]) == {"id", "name", "slug", "status", "created_at", "updated_at"}
    assert {item["id"] for item in payload["memberships"]} == {
        "mbr_lifecycle_owner",
        "mbr_lifecycle_admin",
        "mbr_lifecycle_member",
        "mbr_lifecycle_viewer",
    }
    assert payload["invitations"] == [{
        "id": pending["id"],
        "destination_email": "export-recipient@example.test",
        "role": "member",
        "status": "pending",
        "expires_at": payload["invitations"][0]["expires_at"],
        "created_at": payload["invitations"][0]["created_at"],
        "accepted_at": None,
        "revoked_at": None,
        "supersedes_id": None,
    }]
    assert payload["seat_projection"] == {
        "limit": 5,
        "active": 4,
        "reserved": 1,
        "consumed": 5,
        "remaining": 0,
    }
    assert payload["plan"] == {"id": "plan_portfolio_org_v1", "key": "portfolio-org-v1", "version": 1}
    _assert_no_sensitive_invitation_data(payload, pending["token"])

    listed = client.get(
        "/api/organizations/org_lifecycle_export/invitations",
        headers=_auth("lifecycle-owner-token"),
    )
    assert listed.status_code == 200
    _assert_no_sensitive_invitation_data(listed.json(), pending["token"])
    for token, expected_status in (
        ("lifecycle-member-token", 403),
        ("lifecycle-viewer-token", 403),
        ("lifecycle-outsider-token", 404),
        ("lifecycle-platform-admin-token", 403),
    ):
        assert client.get(
            "/api/organizations/org_lifecycle_export/export",
            headers=_auth(token),
        ).status_code == expected_status

    with Session() as db:
        events = db.execute(
            select(AccessAuditEventModel).where(AccessAuditEventModel.action == "organization.exported")
        ).scalars().all()
        assert len(events) == 2
        assert all(event.metadata_json == {"membership_count": 4, "invitation_count": 1} for event in events)


def test_disabled_lifecycle_owner_can_export_but_deleted_organization_cannot(lifecycle_export_client):
    client, _, _ = lifecycle_export_client
    assert client.patch(
        "/api/organizations/org_lifecycle_export",
        json={"status": "disabled"},
        headers=_auth("lifecycle-owner-token"),
    ).status_code == 200
    assert client.get(
        "/api/organizations/org_lifecycle_export/export",
        headers=_auth("lifecycle-owner-token"),
    ).status_code == 200
    for token in (
        "lifecycle-admin-token",
        "lifecycle-member-token",
        "lifecycle-viewer-token",
        "lifecycle-platform-admin-token",
    ):
        assert client.get(
            "/api/organizations/org_lifecycle_export/export",
            headers=_auth(token),
        ).status_code == 403

    assert client.delete(
        "/api/organizations/org_lifecycle_export",
        headers=_auth("lifecycle-owner-token"),
    ).status_code == 200
    assert client.get(
        "/api/organizations/org_lifecycle_export/export",
        headers=_auth("lifecycle-owner-token"),
    ).status_code == 404


def test_seat_projection_is_member_scoped_and_keeps_disabled_owner_recovery(lifecycle_export_client):
    client, _, _ = lifecycle_export_client
    for token in ("lifecycle-owner-token", "lifecycle-member-token", "lifecycle-viewer-token"):
        response = client.get(
            "/api/organizations/org_lifecycle_export/seat-status",
            headers=_auth(token),
        )
        assert response.status_code == 200
        assert response.json() == {
            "limit": 5,
            "active": 4,
            "reserved": 0,
            "consumed": 4,
            "remaining": 1,
        }
    assert client.get(
        "/api/organizations/org_lifecycle_export/seat-status",
        headers=_auth("lifecycle-platform-admin-token"),
    ).status_code == 404

    assert client.patch(
        "/api/organizations/org_lifecycle_export",
        json={"status": "disabled"},
        headers=_auth("lifecycle-owner-token"),
    ).status_code == 200
    assert client.get(
        "/api/organizations/org_lifecycle_export/seat-status",
        headers=_auth("lifecycle-owner-token"),
    ).status_code == 200
    assert client.get(
        "/api/organizations/org_lifecycle_export/seat-status",
        headers=_auth("lifecycle-admin-token"),
    ).status_code == 404


def test_invitation_responses_and_audits_never_serialize_tokens_or_hashes(lifecycle_export_client):
    client, Session, identities = lifecycle_export_client
    first = _invite(
        client,
        "org_lifecycle_export",
        "lifecycle-owner-token",
        "metadata-recipient@example.test",
    )
    resent = client.post(
        f"/api/organizations/org_lifecycle_export/invitations/{first['id']}/resend",
        headers=_auth("lifecycle-owner-token"),
    )
    assert resent.status_code == 200
    replacement = resent.json()
    assert replacement["token"] != first["token"]
    revoked = client.post(
        f"/api/organizations/org_lifecycle_export/invitations/{replacement['id']}/revoke",
        headers=_auth("lifecycle-owner-token"),
    )
    assert revoked.status_code == 200
    _assert_no_sensitive_invitation_data(revoked.json(), replacement["token"])
    accepted = _invite(
        client,
        "org_lifecycle_export",
        "lifecycle-owner-token",
        identities["recipient_email"],
    )
    assert client.post(
        "/api/organization-invitations/accept",
        json={"token": accepted["token"]},
        headers=_auth("lifecycle-recipient-token"),
    ).status_code == 200
    failed_acceptance = client.post(
        "/api/organization-invitations/accept",
        json={"token": first["token"]},
        headers=_auth("lifecycle-recipient-token"),
    )
    assert failed_acceptance.status_code == 409
    assert first["token"] not in failed_acceptance.text

    with Session() as db:
        invitation_hashes = [
            item.token_hash
            for item in db.execute(select(OrganizationInvitationModel)).scalars().all()
        ]
        invitation_events = db.execute(
            select(AccessAuditEventModel).where(
                AccessAuditEventModel.action.in_({
                    "invitation.created",
                    "invitation.resent",
                    "invitation.revoked",
                    "invitation.accepted",
                })
            )
        ).scalars().all()
        assert {event.action for event in invitation_events} == {
            "invitation.created",
            "invitation.resent",
            "invitation.revoked",
            "invitation.accepted",
        }
        audit_payload = json.dumps([event.metadata_json for event in invitation_events])
        for value in [first["token"], replacement["token"], accepted["token"], *invitation_hashes]:
            assert value not in audit_payload
        assert "token" not in audit_payload.lower()
        assert "hash" not in audit_payload.lower()


def _invite(client: TestClient, organization_id: str, token: str, email: str) -> dict:
    response = client.post(
        f"/api/organizations/{organization_id}/invitations",
        json={"email": email, "role": "member"},
        headers=_auth(token),
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["token"]
    return payload


def _assert_no_sensitive_invitation_data(payload: dict, plaintext_token: str) -> None:
    serialized = json.dumps(payload).lower()
    assert plaintext_token not in json.dumps(payload)
    for forbidden in ("token", "hash", "jwt", "auth_time", "secret", "billing", "report", "strategy", "private"):
        assert forbidden not in serialized


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}
