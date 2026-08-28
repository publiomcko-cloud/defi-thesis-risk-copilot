from __future__ import annotations

import logging

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy import create_engine

from app.auth.service import create_user
from app.core.config import get_settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.access_audit_event import AccessAuditEventModel
from app.models.customer_request import CustomerRequestModel
from app.models.organization import OrganizationMembershipModel, OrganizationModel
from app.models.product_analytics import ProductAnalyticsEventModel
from app.models.user import UserModel
from app.product_analytics.registry import EVENT_DEFINITIONS


REQUEST_TYPES = (
    "support",
    "feedback",
    "abuse_report",
    "privacy_access_export",
    "privacy_deletion",
)


@pytest.fixture
def customer_requests_client(monkeypatch):
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("AUTH_PROVIDER", "legacy_local")
    monkeypatch.setenv("AUTH_SECRET_KEY", "phase20i-customer-request-secret")
    monkeypatch.setenv("APP_ENV", "development")
    get_settings.cache_clear()
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    with sessions() as db:
        owner = create_user(db, "customer-owner@example.test", token="customer-owner-token")
        other = create_user(db, "customer-other@example.test", token="customer-other-token")
        member = create_user(db, "customer-member@example.test", token="customer-member-token")
        organization_admin = create_user(db, "customer-org-admin@example.test", token="customer-org-admin-token")
        outsider = create_user(db, "customer-outsider@example.test", token="customer-outsider-token")
        platform_admin = create_user(
            db,
            "customer-platform-admin@example.test",
            role="admin",
            token="customer-platform-admin-token",
        )
        organization = OrganizationModel(
            id="org_customer_requests",
            name="Customer requests",
            slug="customer-requests",
            status="active",
            created_by_user_id=owner.id,
        )
        db.add(organization)
        db.flush()
        db.add_all([
            OrganizationMembershipModel(
                id="mbr_customer_owner",
                organization_id=organization.id,
                user_id=owner.id,
                role="owner",
                status="active",
            ),
            OrganizationMembershipModel(
                id="mbr_customer_member",
                organization_id=organization.id,
                user_id=member.id,
                role="member",
                status="active",
            ),
            OrganizationMembershipModel(
                id="mbr_customer_admin",
                organization_id=organization.id,
                user_id=organization_admin.id,
                role="admin",
                status="active",
            ),
        ])
        db.commit()
        identities = {
            "owner_id": owner.id,
            "other_id": other.id,
            "member_id": member.id,
            "organization_admin_id": organization_admin.id,
            "outsider_id": outsider.id,
            "platform_admin_id": platform_admin.id,
            "organization_id": organization.id,
        }

    def override_get_db():
        db = sessions()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app), sessions, identities
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()


@pytest.mark.parametrize("request_type", REQUEST_TYPES)
def test_exact_request_taxonomy_and_server_derived_states(customer_requests_client, request_type):
    client, Session, identities = customer_requests_client
    response = _create(client, request_type=request_type)
    assert response.status_code == 201
    payload = response.json()
    assert payload["request_type"] == request_type
    assert payload["workflow_state"] == "open"
    assert payload["verification_state"] == (
        "authenticated" if request_type.startswith("privacy_") else "not_required"
    )
    with Session() as db:
        record = db.get(CustomerRequestModel, payload["id"])
        assert record is not None and record.owner_user_id == identities["owner_id"]


def test_request_input_is_bounded_and_cannot_author_server_fields(customer_requests_client):
    client, _, _ = customer_requests_client
    for payload in (
        {"request_type": "unknown", "subject": "Subject", "description": "Description"},
        {"request_type": "support", "subject": "S" * 121, "description": "Description"},
        {"request_type": "support", "subject": "Subject", "description": "D" * 4001},
        {"request_type": "support", "subject": "Subject", "description": "Description", "attachments": []},
        {"request_type": "support", "subject": "Subject", "description": "Description", "owner_user_id": "other"},
        {"request_type": "support", "subject": "Subject", "description": "Description", "workflow_state": "closed"},
        {"request_type": "support", "subject": "Subject", "description": "Description", "verification_state": "authenticated"},
    ):
        response = client.post("/api/customer-requests", json=payload, headers=_auth("customer-owner-token"))
        assert response.status_code == 422
        assert "Subject" not in response.text and "Description" not in response.text

    unauthenticated = client.post(
        "/api/customer-requests",
        json={"request_type": "support", "subject": "Subject", "description": "Description"},
    )
    assert unauthenticated.status_code == 401


def test_owner_isolation_and_deterministic_close(customer_requests_client):
    client, Session, _ = customer_requests_client
    created = _create(client).json()
    request_id = created["id"]
    for token in ("customer-other-token", "customer-org-admin-token", "customer-platform-admin-token"):
        for method, path in (
            (client.get, f"/api/customer-requests/{request_id}"),
            (client.post, f"/api/customer-requests/{request_id}/close"),
        ):
            response = method(path, headers=_auth(token))
            assert response.status_code == 404
        assert client.get("/api/customer-requests", headers=_auth(token)).json()["items"] == []

    first = client.post(f"/api/customer-requests/{request_id}/close", headers=_auth("customer-owner-token"))
    second = client.post(f"/api/customer-requests/{request_id}/close", headers=_auth("customer-owner-token"))
    assert first.status_code == second.status_code == 200
    assert first.json()["workflow_state"] == second.json()["workflow_state"] == "closed"
    assert first.json()["closed_at"] == second.json()["closed_at"]
    with Session() as db:
        close_audits = db.execute(
            select(AccessAuditEventModel).where(AccessAuditEventModel.action == "customer_request.closed")
        ).scalars().all()
        assert len(close_audits) == 1


def test_organization_context_is_server_authorized_and_privacy_is_individual(customer_requests_client):
    client, Session, identities = customer_requests_client
    contextual = _create(client, organization_id=identities["organization_id"])
    assert contextual.status_code == 201
    assert contextual.json()["organization_id"] == identities["organization_id"]
    member_context = client.post(
        "/api/customer-requests",
        json={
            "request_type": "feedback",
            "subject": "Member context",
            "description": "An active member may attach active organization context.",
            "organization_id": identities["organization_id"],
        },
        headers=_auth("customer-member-token"),
    )
    assert member_context.status_code == 201
    assert client.get(
        f"/api/customer-requests/{member_context.json()['id']}",
        headers=_auth("customer-owner-token"),
    ).status_code == 404
    nonmember = client.post(
        "/api/customer-requests",
        json={
            "request_type": "support",
            "subject": "Nonmember context",
            "description": "A nonmember cannot attach this organization.",
            "organization_id": identities["organization_id"],
        },
        headers=_auth("customer-outsider-token"),
    )
    assert nonmember.status_code == 404
    privacy_context = _create(
        client,
        request_type="privacy_access_export",
        organization_id=identities["organization_id"],
    )
    assert privacy_context.status_code == 422
    with Session() as db:
        db.get(OrganizationModel, identities["organization_id"]).status = "disabled"
        db.commit()
    disabled = _create(client, organization_id=identities["organization_id"])
    assert disabled.status_code == 404


def test_private_content_stays_out_of_logs_audits_analytics_and_pipelines(
    customer_requests_client,
    monkeypatch,
    caplog,
):
    client, Session, identities = customer_requests_client
    subject = "Private customer request subject 20I"
    description = "Private customer request description must remain in the owner row only."

    def forbidden(*_args, **_kwargs):
        raise AssertionError("customer request text must not enter a model or retrieval pipeline")

    monkeypatch.setattr("app.agents.orchestrator.run_analysis_workflow", forbidden)
    monkeypatch.setattr("app.llm.synthesis.synthesize_report", forbidden)
    monkeypatch.setattr("app.knowledge.embedding_service.submit_document_embedding", forbidden)
    monkeypatch.setattr("app.knowledge.shadow_retriever.retrieve_shadow_knowledge", forbidden)
    caplog.set_level(logging.INFO)
    response = client.post(
        "/api/customer-requests",
        json={"request_type": "support", "subject": subject, "description": description},
        headers=_auth("customer-owner-token"),
    )
    assert response.status_code == 201
    request_id = response.json()["id"]
    assert client.get(f"/api/customer-requests/{request_id}", headers=_auth("customer-owner-token")).status_code == 200
    assert client.post(f"/api/customer-requests/{request_id}/close", headers=_auth("customer-owner-token")).status_code == 200
    assert subject not in caplog.text and description not in caplog.text
    assert not any("customer_request" in event_name for event_name in EVENT_DEFINITIONS)
    with Session() as db:
        events = db.execute(
            select(AccessAuditEventModel).where(AccessAuditEventModel.resource_id == request_id)
        ).scalars().all()
        assert {event.action for event in events} == {"customer_request.created", "customer_request.closed"}
        for event in events:
            serialized = str(event.metadata_json)
            assert subject not in serialized and description not in serialized
        assert db.scalar(
            select(func.count()).select_from(ProductAnalyticsEventModel).where(
                ProductAnalyticsEventModel.owner_user_id == identities["owner_id"]
            )
        ) == 0


def test_account_export_deletion_and_organization_deletion_preserve_owner_isolation(customer_requests_client):
    client, Session, identities = customer_requests_client
    exported_request = _create(client, request_type="feedback").json()
    contextual_request = _create(client, organization_id=identities["organization_id"]).json()
    export = client.get("/api/account/export", headers=_auth("customer-owner-token"))
    assert export.status_code == 200
    exported = {item["id"]: item for item in export.json()["customer_requests"]}
    assert exported[exported_request["id"]]["subject"] == "Customer request subject"
    assert exported[exported_request["id"]]["description"] == "Customer request description"
    assert "metadata" not in exported[exported_request["id"]]

    deleted_org = client.delete(
        f"/api/organizations/{identities['organization_id']}",
        headers=_auth("customer-owner-token"),
    )
    assert deleted_org.status_code == 200
    with Session() as db:
        preserved = db.get(CustomerRequestModel, contextual_request["id"])
        assert preserved is not None and preserved.owner_user_id == identities["owner_id"]
        assert preserved.organization_id is None

    account_request = client.post(
        "/api/customer-requests",
        json={"request_type": "support", "subject": "Other account", "description": "Remove this with the account."},
        headers=_auth("customer-other-token"),
    )
    assert account_request.status_code == 201
    deleted_account = client.request(
        "DELETE",
        "/api/account",
        json={"confirmation": "DELETE"},
        headers=_auth("customer-other-token"),
    )
    assert deleted_account.status_code == 200
    with Session() as db:
        assert db.get(CustomerRequestModel, account_request.json()["id"]) is None
        assert db.get(UserModel, identities["other_id"]).account_status == "deleted"


def _create(client: TestClient, *, request_type: str = "support", organization_id: str | None = None):
    payload = {
        "request_type": request_type,
        "subject": "Customer request subject",
        "description": "Customer request description",
    }
    if organization_id is not None:
        payload["organization_id"] = organization_id
    return client.post("/api/customer-requests", json=payload, headers=_auth("customer-owner-token"))


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}
