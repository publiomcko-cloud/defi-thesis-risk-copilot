from __future__ import annotations

import asyncio

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.service import create_user, user_context
from app.core.config import get_settings
from app.db.base import Base
from app.db.session import get_db
from app.knowledge.schemas import KnowledgeSourceCreateRequest
from app.knowledge.service import create_document_upload, create_source
from app.main import app
from app.models.access_audit_event import AccessAuditEventModel
from app.models.knowledge import (
    KnowledgeDocumentModel,
    KnowledgeDocumentVersionModel,
    KnowledgeSourceModel,
)
from app.models.user import UserModel
from app.storage.memory import InMemoryPrivateObjectStorage


@pytest.fixture()
def knowledge_api_client(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("AUTH_PROVIDER", "legacy_local")
    monkeypatch.setenv("AUTH_SECRET_KEY", "phase18b-test-secret")
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("KNOWLEDGE_STORAGE_ENABLED", "true")
    get_settings.cache_clear()
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    with Session() as db:
        create_user(db, "owner@example.test", token="owner-token")
        create_user(db, "outsider@example.test", token="outsider-token")
        create_user(db, "admin@example.test", role="admin", token="admin-token")

    storage = InMemoryPrivateObjectStorage()
    monkeypatch.setattr("app.knowledge.service.create_private_object_storage", lambda: storage)

    def override_get_db():
        session = Session()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app), Session, storage
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()


def test_private_upload_is_owner_scoped_and_does_not_expose_storage_details(
    knowledge_api_client,
) -> None:
    client, Session, storage = knowledge_api_client
    created = client.post(
        "/api/knowledge/sources",
        headers=_auth("owner-token"),
        json=_private_source_payload(),
    )
    assert created.status_code == 200
    source = created.json()
    assert source["owner_user_id"]
    assert source["trust_state"] == "needs_review"

    uploaded = client.post(
        f"/api/knowledge/sources/{source['id']}/documents",
        headers=_auth("owner-token"),
        files={"file": ("risk.md", b"# Private risk controls\n", "text/markdown")},
    )
    assert uploaded.status_code == 200
    document = uploaded.json()
    assert document["status"] == "uploaded"
    assert document["versions"][0]["status"] == "uploaded"
    assert "storage_key" not in str(document)
    assert "signed" not in str(document).lower()
    assert len(storage._objects) == 1

    assert client.get(
        f"/api/knowledge/sources/{source['id']}", headers=_auth("outsider-token")
    ).status_code == 404
    assert client.get(
        f"/api/knowledge/documents/{document['id']}", headers=_auth("outsider-token")
    ).status_code == 404
    assert client.post(
        f"/api/knowledge/documents/{document['id']}/versions",
        headers=_auth("outsider-token"),
        files={"file": ("risk.md", b"unauthorized", "text/markdown")},
    ).status_code == 404

    with Session() as db:
        event = db.execute(
            select(AccessAuditEventModel).where(
                AccessAuditEventModel.action == "knowledge.document_uploaded"
            )
        ).scalars().one()
        assert event.metadata_json["document_id"] == document["id"]
        assert "storage_key" not in event.metadata_json


def test_source_document_list_and_admin_readiness_preserve_tenant_and_secret_boundaries(
    knowledge_api_client,
) -> None:
    client, _, _ = knowledge_api_client
    source_id = _create_private_source(client)
    uploaded = client.post(
        f"/api/knowledge/sources/{source_id}/documents",
        headers=_auth("owner-token"),
        files={"file": ("lineage.md", b"# Lineage", "text/markdown")},
    ).json()

    listed = client.get(
        f"/api/knowledge/sources/{source_id}/documents", headers=_auth("owner-token")
    )
    assert listed.status_code == 200
    assert listed.json()["items"][0]["id"] == uploaded["id"]
    assert listed.json()["items"][0]["versions"][0]["id"].startswith("kver_")
    assert "storage_key" not in str(listed.json())
    assert client.get(
        f"/api/knowledge/sources/{source_id}/documents", headers=_auth("outsider-token")
    ).status_code == 404

    assert client.get("/api/knowledge/readiness", headers=_auth("owner-token")).status_code == 403
    readiness = client.get("/api/knowledge/readiness", headers=_auth("admin-token"))
    assert readiness.status_code == 200
    payload = readiness.json()
    assert payload["database_ready"] is True
    assert payload["storage_enabled"] is True
    assert payload["visible_source_count"] >= 1
    assert "storage_key" not in str(payload)
    assert "secret" not in str(payload).lower()


def test_account_export_includes_only_safe_private_knowledge_metadata(
    knowledge_api_client,
) -> None:
    client, _, _ = knowledge_api_client
    source_id = _create_private_source(client)
    uploaded = client.post(
        f"/api/knowledge/sources/{source_id}/documents",
        headers=_auth("owner-token"),
        files={"file": ("account-export.md", b"# private content", "text/markdown")},
    ).json()

    exported = client.get("/api/account/export", headers=_auth("owner-token"))
    assert exported.status_code == 200
    payload = exported.json()
    assert payload["format_version"] == "phase17.account_export.v2"
    assert payload["knowledge_sources"][0]["id"] == source_id
    assert payload["knowledge_documents"][0]["id"] == uploaded["id"]
    assert payload["knowledge_document_versions"][0]["id"].startswith("kver_")
    rendered = str(payload)
    assert "storage_key" not in rendered
    assert "signed" not in rendered.lower()
    assert "private content" not in rendered
    assert "embedding_json" not in rendered


def test_upload_validation_and_disabled_storage_leave_no_document(knowledge_api_client, monkeypatch) -> None:
    client, Session, _ = knowledge_api_client
    source_id = _create_private_source(client)
    wrong_checksum = client.post(
        f"/api/knowledge/sources/{source_id}/documents",
        headers=_auth("owner-token"),
        data={"checksum": "0" * 64},
        files={"file": ("risk.md", b"# Valid markdown", "text/markdown")},
    )
    assert wrong_checksum.status_code == 422
    invalid_type = client.post(
        f"/api/knowledge/sources/{source_id}/documents",
        headers=_auth("owner-token"),
        files={"file": ("risk.exe", b"binary", "application/octet-stream")},
    )
    assert invalid_type.status_code == 422

    from app.storage.base import StorageConfigurationError

    monkeypatch.setattr(
        "app.knowledge.service.create_private_object_storage",
        lambda: (_ for _ in ()).throw(StorageConfigurationError("disabled")),
    )
    disabled = client.post(
        f"/api/knowledge/sources/{source_id}/documents",
        headers=_auth("owner-token"),
        files={"file": ("risk.md", b"# Valid markdown", "text/markdown")},
    )
    assert disabled.status_code == 503
    with Session() as db:
        assert db.execute(select(KnowledgeDocumentModel)).scalars().all() == []
        assert db.execute(select(KnowledgeDocumentVersionModel)).scalars().all() == []


def test_upload_compensates_written_object_when_database_commit_fails(
    knowledge_api_client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, Session, storage = knowledge_api_client
    with Session() as db:
        owner = db.execute(
            select(UserModel).where(UserModel.email == "owner@example.test")
        ).scalars().one()
        source = create_source(
            db,
            user_context(owner),
            KnowledgeSourceCreateRequest(**_private_source_payload()),
        )
        document_content = b"# Compensated upload\n"

        class Upload:
            filename = "risk.md"
            content_type = "text/markdown"

            def __init__(self) -> None:
                self._sent = False

            async def read(self, _: int) -> bytes:
                if self._sent:
                    return b""
                self._sent = True
                return document_content

        original_commit = db.commit

        def failed_commit() -> None:
            raise SQLAlchemyError("forced database failure")

        monkeypatch.setattr(db, "commit", failed_commit)
        with pytest.raises(HTTPException) as failed:
            asyncio.run(create_document_upload(db, user_context(owner), source.id, Upload(), None))
        assert failed.value.status_code == 503
        monkeypatch.setattr(db, "commit", original_commit)
        assert storage._objects == {}
        assert db.execute(select(KnowledgeDocumentModel)).scalars().all() == []


def test_source_approval_is_audited_and_ingestion_is_not_available(knowledge_api_client) -> None:
    client, Session, _ = knowledge_api_client
    source_id = _create_private_source(client)
    approved = client.patch(
        f"/api/knowledge/sources/{source_id}",
        headers=_auth("owner-token"),
        json={"trust_state": "approved_for_rag"},
    )
    assert approved.status_code == 200
    assert approved.json()["trust_state"] == "approved_for_rag"
    assert approved.json()["approved_by_user_id"]
    forbidden_state = client.patch(
        f"/api/knowledge/sources/{source_id}",
        headers=_auth("owner-token"),
        json={"status": "ingestion_pending"},
    )
    assert forbidden_state.status_code == 422
    assert client.post(
        "/api/knowledge/document-versions/kver_unknown/ingest",
        headers={**_auth("owner-token"), "Idempotency-Key": "phase18b-disabled-key"},
    ).status_code == 503
    assert client.post(
        "/api/knowledge/document-versions/kver_unknown/embed",
        headers={**_auth("owner-token"), "Idempotency-Key": "phase18d-disabled-key"},
    ).status_code == 503
    with Session() as db:
        source = db.get(KnowledgeSourceModel, source_id)
        assert source is not None
        assert source.status == "registered"
        assert db.execute(
            select(AccessAuditEventModel).where(
                AccessAuditEventModel.action == "knowledge.source_updated"
            )
        ).scalars().one()


def test_organization_uploads_are_member_visible_but_manager_controlled(
    knowledge_api_client,
) -> None:
    client, Session, _ = knowledge_api_client
    with Session() as db:
        create_user(db, "member@example.test", token="member-token")
    organization = client.post(
        "/api/organizations",
        headers=_auth("owner-token"),
        json={"name": "Organization Knowledge"},
    )
    organization_id = organization.json()["id"]
    assert client.post(
        f"/api/organizations/{organization_id}/members",
        headers=_auth("owner-token"),
        json={"email": "member@example.test", "role": "member"},
    ).status_code == 200
    source = client.post(
        "/api/knowledge/sources",
        headers=_auth("owner-token"),
        json={
            "visibility": "organization",
            "organization_id": organization_id,
            "title": "Organization lending policy",
            "source_type": "upload",
        },
    ).json()
    document = client.post(
        f"/api/knowledge/sources/{source['id']}/documents",
        headers=_auth("owner-token"),
        files={"file": ("policy.txt", b"organization-only policy", "text/plain")},
    ).json()

    assert client.get(
        f"/api/knowledge/documents/{document['id']}", headers=_auth("member-token")
    ).status_code == 200
    assert client.post(
        f"/api/knowledge/documents/{document['id']}/versions",
        headers=_auth("member-token"),
        files={"file": ("policy.txt", b"member cannot modify", "text/plain")},
    ).status_code == 403
    assert client.get(
        f"/api/knowledge/documents/{document['id']}", headers=_auth("outsider-token")
    ).status_code == 404


def test_document_delete_tombstones_versions_without_deleting_storage_immediately(
    knowledge_api_client,
) -> None:
    client, Session, storage = knowledge_api_client
    source_id = _create_private_source(client)
    uploaded = client.post(
        f"/api/knowledge/sources/{source_id}/documents",
        headers=_auth("owner-token"),
        files={"file": ("delete.txt", b"retention-managed object", "text/plain")},
    ).json()
    deleted = client.delete(
        f"/api/knowledge/documents/{uploaded['id']}", headers=_auth("owner-token")
    )
    assert deleted.status_code == 200
    assert deleted.json()["status"] == "deleted"
    assert deleted.json()["versions"][0]["status"] == "deleted"
    assert len(storage._objects) == 1
    assert client.get(
        f"/api/knowledge/documents/{uploaded['id']}", headers=_auth("owner-token")
    ).status_code == 404
    with Session() as db:
        assert db.execute(
            select(AccessAuditEventModel).where(
                AccessAuditEventModel.action == "knowledge.document_deleted"
            )
        ).scalars().one()


def test_account_and_organization_deletion_tombstone_knowledge(knowledge_api_client) -> None:
    client, Session, _ = knowledge_api_client
    source_id = _create_private_source(client)
    account_deleted = client.request(
        "DELETE",
        "/api/account",
        headers=_auth("owner-token"),
        json={"confirmation": "DELETE"},
    )
    assert account_deleted.status_code == 200
    with Session() as db:
        source = db.get(KnowledgeSourceModel, source_id)
        assert source is not None
        assert source.status == "deleted"
        assert source.deleted_at is not None

    # A fresh owner can create and delete an organization, which tombstones its sources.
    with Session() as db:
        create_user(db, "org-owner@example.test", token="org-owner-token")
    organization = client.post(
        "/api/organizations",
        headers=_auth("org-owner-token"),
        json={"name": "Phase 18B Organization"},
    )
    organization_id = organization.json()["id"]
    org_source = client.post(
        "/api/knowledge/sources",
        headers=_auth("org-owner-token"),
        json={
            "visibility": "organization",
            "organization_id": organization_id,
            "title": "Organization source",
            "source_type": "upload",
        },
    )
    assert org_source.status_code == 200
    assert client.delete(
        f"/api/organizations/{organization_id}", headers=_auth("org-owner-token")
    ).status_code == 200
    with Session() as db:
        source = db.get(KnowledgeSourceModel, org_source.json()["id"])
        assert source is not None
        assert source.status == "deleted"
        assert source.deleted_at is not None


def _create_private_source(client: TestClient) -> str:
    response = client.post(
        "/api/knowledge/sources",
        headers=_auth("owner-token"),
        json=_private_source_payload(),
    )
    assert response.status_code == 200
    return response.json()["id"]


def _private_source_payload() -> dict:
    return {
        "visibility": "private",
        "title": "Private lending research",
        "source_type": "upload",
        "protocol": "aave",
    }


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}
