from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.service import create_user, user_context
from app.core.config import get_settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.organization import OrganizationMembershipModel, OrganizationModel
from app.models.user import UserModel
from app.rag.embeddings import LocalHashEmbeddingProvider
from app.rag.hybrid_retriever import HybridRetriever
from app.rag.retriever import Retriever
from app.rag.scope import derive_retrieval_scope
from app.rag.vector_store import JsonVectorStore
from app.schemas.analysis import AnalysisRequest


@pytest.fixture()
def knowledge_client(monkeypatch):
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("AUTH_PROVIDER", "legacy_local")
    monkeypatch.setenv("AUTH_SECRET_KEY", "phase16-knowledge-secret")
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
        create_user(db, "owner@example.test", token="owner-token")
        create_user(db, "member@example.test", token="member-token")
        create_user(db, "org-admin@example.test", token="org-admin-token")
        create_user(db, "outsider@example.test", token="outsider-token")
        create_user(db, "platform-admin@example.test", role="admin", token="admin-token")

    def override_get_db():
        session = Session()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app), Session
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()


def test_organization_knowledge_metadata_is_member_scoped_and_manager_controlled(
    knowledge_client,
) -> None:
    client, _ = knowledge_client
    organization_id = _create_org_with_member(client)
    source = client.post(
        f"/api/organizations/{organization_id}/knowledge-sources",
        headers=_auth("owner-token"),
        json=_source_payload(),
    )

    assert source.status_code == 200
    source_payload = source.json()
    assert source_payload["organization_id"] == organization_id
    assert source_payload["approval_status"] == "approved"
    assert source_payload["storage_status"] == "metadata_only"
    assert len(source_payload["provenance_hash"]) == 64

    org_admin_create = client.post(
        f"/api/organizations/{organization_id}/knowledge-sources",
        headers=_auth("org-admin-token"),
        json={**_source_payload(), "source_url": "https://docs.example.test/admin-approved"},
    )
    assert org_admin_create.status_code == 200

    member_list = client.get(
        f"/api/organizations/{organization_id}/knowledge-sources",
        headers=_auth("member-token"),
    )
    member_create = client.post(
        f"/api/organizations/{organization_id}/knowledge-sources",
        headers=_auth("member-token"),
        json={**_source_payload(), "source_url": "https://docs.example.test/member"},
    )
    outsider_list = client.get(
        f"/api/organizations/{organization_id}/knowledge-sources",
        headers=_auth("outsider-token"),
    )
    platform_admin_list = client.get(
        f"/api/organizations/{organization_id}/knowledge-sources",
        headers=_auth("admin-token"),
    )

    assert member_list.status_code == 200
    assert len(member_list.json()["items"]) == 2
    assert member_create.status_code == 403
    assert outsider_list.status_code == 404
    assert platform_admin_list.status_code == 404


def test_removed_member_and_disabled_organization_lose_knowledge_access(
    knowledge_client,
) -> None:
    client, _ = knowledge_client
    organization_id = _create_org_with_member(client)
    created = client.post(
        f"/api/organizations/{organization_id}/knowledge-sources",
        headers=_auth("owner-token"),
        json=_source_payload(),
    )
    assert created.status_code == 200

    members = client.get(
        f"/api/organizations/{organization_id}/members",
        headers=_auth("owner-token"),
    ).json()["items"]
    member_id = next(item["id"] for item in members if item["email"] == "member@example.test")
    removed = client.delete(
        f"/api/organizations/{organization_id}/members/{member_id}",
        headers=_auth("owner-token"),
    )
    assert removed.status_code == 200
    assert client.get(
        f"/api/organizations/{organization_id}/knowledge-sources",
        headers=_auth("member-token"),
    ).status_code == 404

    disabled = client.patch(
        f"/api/organizations/{organization_id}",
        headers=_auth("owner-token"),
        json={"status": "disabled"},
    )
    assert disabled.status_code == 200
    assert client.get(
        f"/api/organizations/{organization_id}/knowledge-sources",
        headers=_auth("owner-token"),
    ).status_code == 404

    deleted_organization_id = _create_org_with_member(client, name="Deleted Research Lab")
    assert client.post(
        f"/api/organizations/{deleted_organization_id}/knowledge-sources",
        headers=_auth("owner-token"),
        json=_source_payload(),
    ).status_code == 200
    assert client.delete(
        f"/api/organizations/{deleted_organization_id}",
        headers=_auth("owner-token"),
    ).status_code == 200
    assert client.get(
        f"/api/organizations/{deleted_organization_id}/knowledge-sources",
        headers=_auth("owner-token"),
    ).status_code == 404


def test_organization_source_requires_explicit_approval_and_is_soft_deleted(
    knowledge_client,
) -> None:
    client, _ = knowledge_client
    organization_id = _create_org_with_member(client)
    rejected = client.post(
        f"/api/organizations/{organization_id}/knowledge-sources",
        headers=_auth("owner-token"),
        json={**_source_payload(), "approval_confirmed": False},
    )
    assert rejected.status_code == 422
    credential_url = client.post(
        f"/api/organizations/{organization_id}/knowledge-sources",
        headers=_auth("owner-token"),
        json={
            **_source_payload(),
            "source_url": "https://user:password@docs.example.test/private",
        },
    )
    assert credential_url.status_code == 422

    created = client.post(
        f"/api/organizations/{organization_id}/knowledge-sources",
        headers=_auth("owner-token"),
        json=_source_payload(),
    )
    source_id = created.json()["id"]
    duplicate = client.post(
        f"/api/organizations/{organization_id}/knowledge-sources",
        headers=_auth("owner-token"),
        json=_source_payload(),
    )
    deleted = client.delete(
        f"/api/organizations/{organization_id}/knowledge-sources/{source_id}",
        headers=_auth("owner-token"),
    )
    remaining = client.get(
        f"/api/organizations/{organization_id}/knowledge-sources",
        headers=_auth("owner-token"),
    )

    assert duplicate.status_code == 409
    assert deleted.status_code == 200
    assert deleted.json()["status"] == "disabled"
    assert remaining.json()["items"] == []


def test_global_ingestion_stays_platform_admin_controlled(knowledge_client, monkeypatch) -> None:
    client, _ = knowledge_client
    monkeypatch.setattr("app.api.routes_documents.ingest_knowledge_base", lambda: [])
    payload = {"protocol": "aave"}

    owner = client.post("/api/documents/ingest", headers=_auth("owner-token"), json=payload)
    admin = client.post("/api/documents/ingest", headers=_auth("admin-token"), json=payload)

    assert owner.status_code == 403
    assert admin.status_code == 200
    assert client.get("/api/knowledge-base/discovered").status_code == 200


def test_retrieval_scope_is_server_derived_and_shared_index_rejects_tenant_chunks(
    knowledge_client,
    tmp_path,
) -> None:
    _, Session = knowledge_client
    with Session() as db:
        owner_user = db.execute(
            select(UserModel).where(UserModel.email == "owner@example.test")
        ).scalars().one()
        org = OrganizationModel(
            id="org_scope_test",
            name="Scope Test",
            slug="scope-test",
            status="active",
            created_by_user_id=owner_user.id,
        )
        membership = OrganizationMembershipModel(
            id="mbr_scope_test",
            organization_id=org.id,
            user_id=owner_user.id,
            role="owner",
            status="active",
        )
        db.add_all([org, membership])
        db.commit()
        actor = user_context(owner_user)
        scope = derive_retrieval_scope(db, actor)

    assert scope.visible_organization_ids == frozenset({"org_scope_test"})
    assert scope.tenant_storage_enabled is False

    embedding_provider = LocalHashEmbeddingProvider()
    store = JsonVectorStore(tmp_path / "scope-index.json")
    store.save(
        [
            _retrieval_record("public", "Public oracle documentation", embedding_provider, {}),
            _retrieval_record(
                "tenant",
                "Private organization oracle configuration",
                embedding_provider,
                {"knowledge_scope": "organization", "organization_id": "org_scope_test"},
            ),
        ]
    )
    results = Retriever(store).retrieve("oracle documentation configuration", top_k=5, scope=scope)
    hybrid_results = HybridRetriever(store, semantic_enabled=False).retrieve(
        "oracle documentation configuration",
        top_k=5,
        scope=scope,
    )

    assert [result.chunk_id for result in results] == ["public"]
    assert [result.chunk_id for result in hybrid_results] == ["public"]

    with Session() as db:
        membership = db.get(OrganizationMembershipModel, "mbr_scope_test")
        membership.status = "removed"
        db.commit()
        assert derive_retrieval_scope(db, actor).visible_organization_ids == frozenset()
        membership.status = "active"
        db.get(OrganizationModel, "org_scope_test").status = "disabled"
        db.commit()
        assert derive_retrieval_scope(db, actor).visible_organization_ids == frozenset()

    with pytest.raises(ValidationError):
        AnalysisRequest.model_validate(
            {
                "strategy_description": "Analyze an Aave lending strategy.",
                "protocols": ["aave"],
                "organization_id": "org_other_tenant",
            }
        )


def _create_org_with_member(client: TestClient, name: str = "Risk Research Lab") -> str:
    organization = client.post(
        "/api/organizations",
        headers=_auth("owner-token"),
        json={"name": name},
    )
    assert organization.status_code == 200
    organization_id = organization.json()["id"]
    member = client.post(
        f"/api/organizations/{organization_id}/members",
        headers=_auth("owner-token"),
        json={"email": "member@example.test", "role": "member"},
    )
    assert member.status_code == 200
    org_admin = client.post(
        f"/api/organizations/{organization_id}/members",
        headers=_auth("owner-token"),
        json={"email": "org-admin@example.test", "role": "admin"},
    )
    assert org_admin.status_code == 200
    return organization_id


def _source_payload() -> dict:
    return {
        "title": "Example lending documentation",
        "protocol": "Example",
        "source_type": "documentation",
        "source_url": "https://docs.example.test/lending",
        "approval_confirmed": True,
        "approval_notes": "Reviewed by the organization owner for research provenance.",
    }


def _retrieval_record(
    record_id: str,
    text: str,
    embedding_provider: LocalHashEmbeddingProvider,
    metadata: dict,
) -> dict:
    return {
        "id": record_id,
        "text": text,
        "embedding": embedding_provider.embed(text),
        "metadata": {
            "protocol": "example",
            "source_url": "https://docs.example.test/",
            "document_title": "Example docs",
            "section_title": "Oracle documentation",
            **metadata,
        },
    }


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}
