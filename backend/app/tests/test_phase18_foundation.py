from __future__ import annotations

from datetime import timedelta

import httpx
import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.service import create_user, user_context
from app.core.config import Settings, get_settings
from app.db.base import Base
from app.jobs.control_service import submit_job
from app.jobs.registry import (
    executor_for_job_type,
    validate_result_schema,
    validate_submission_schema,
)
from app.jobs.schemas import JobResultEnvelope, JobSubmissionRequest
from app.knowledge.access import (
    can_manage_knowledge_source,
    create_knowledge_source,
    get_visible_knowledge_source,
    list_visible_knowledge_sources,
    trusted_knowledge_sources_statement,
)
from app.models.knowledge import (
    KnowledgeDocumentModel,
    KnowledgeDocumentVersionModel,
    KnowledgeSourceModel,
)
from app.models.organization import OrganizationMembershipModel, OrganizationModel
from app.storage.base import (
    ObjectConflictError,
    ObjectNotFoundError,
    StorageConfigurationError,
    StorageError,
)
from app.storage.factory import create_private_object_storage
from app.storage.keys import build_version_object_key, validate_knowledge_object_key
from app.storage.memory import InMemoryPrivateObjectStorage
from app.storage.supabase import SupabasePrivateObjectStorage


@pytest.fixture()
def phase18_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    try:
        yield Session
    finally:
        get_settings.cache_clear()


def test_private_sources_are_owner_scoped_and_server_derived(phase18_session) -> None:
    with phase18_session() as db:
        owner = create_user(db, "phase18-owner@example.test")
        outsider = create_user(db, "phase18-outsider@example.test")
        source = create_knowledge_source(
            db,
            user_context(owner),
            visibility="private",
            title="Private Aave policy",
            source_type="upload",
            source_uri="private://caller-does-not-control-storage-key",
        )
        db.commit()

        assert source.owner_user_id == owner.id
        assert source.organization_id is None
        assert source.trust_state == "needs_review"
        assert [item.id for item in list_visible_knowledge_sources(db, user_context(owner))] == [
            source.id
        ]
        assert list_visible_knowledge_sources(db, user_context(outsider)) == []
        assert can_manage_knowledge_source(db, user_context(owner), source) is True
        assert can_manage_knowledge_source(db, user_context(outsider), source) is False
        with pytest.raises(HTTPException) as denied:
            get_visible_knowledge_source(db, user_context(outsider), source.id)
        assert denied.value.status_code == 404


def test_anonymous_context_cannot_create_durable_knowledge(phase18_session) -> None:
    with phase18_session() as db:
        anonymous = user_context(create_user(db, "phase18-anonymous@example.test"))
        anonymous.auth_enabled = False
        with pytest.raises(HTTPException) as denied:
            create_knowledge_source(
                db,
                anonymous,
                visibility="private",
                title="Anonymous durable source",
                source_type="upload",
            )
        assert denied.value.status_code == 403


def test_organization_sources_require_manager_and_active_membership(
    phase18_session,
) -> None:
    with phase18_session() as db:
        owner = create_user(db, "phase18-org-owner@example.test")
        member = create_user(db, "phase18-org-member@example.test")
        outsider = create_user(db, "phase18-org-outsider@example.test")
        platform_admin = create_user(db, "phase18-platform-admin@example.test", role="admin")
        organization = OrganizationModel(
            id="org_phase18_access",
            name="Phase 18 Access",
            slug="phase-18-access",
            status="active",
            created_by_user_id=owner.id,
        )
        db.add(organization)
        db.flush()
        owner_membership = OrganizationMembershipModel(
            id="mbr_phase18_owner",
            organization_id=organization.id,
            user_id=owner.id,
            role="owner",
            status="active",
        )
        member_membership = OrganizationMembershipModel(
            id="mbr_phase18_member",
            organization_id=organization.id,
            user_id=member.id,
            role="member",
            status="active",
        )
        db.add_all([owner_membership, member_membership])
        db.commit()

        source = create_knowledge_source(
            db,
            user_context(owner),
            visibility="organization",
            organization_id=organization.id,
            title="Organization risk policy",
            source_type="upload",
        )
        db.commit()

        assert source.owner_user_id == owner.id
        assert source.organization_id == organization.id
        assert get_visible_knowledge_source(db, user_context(member), source.id).id == source.id
        assert can_manage_knowledge_source(db, user_context(member), source) is False
        assert can_manage_knowledge_source(db, user_context(owner), source) is True
        for actor in (outsider, platform_admin):
            with pytest.raises(HTTPException) as denied:
                get_visible_knowledge_source(db, user_context(actor), source.id)
            assert denied.value.status_code == 404
        with pytest.raises(HTTPException) as member_create:
            create_knowledge_source(
                db,
                user_context(member),
                visibility="organization",
                organization_id=organization.id,
                title="Member cannot approve a source",
                source_type="upload",
            )
        assert member_create.value.status_code == 403

        member_membership.status = "removed"
        db.commit()
        with pytest.raises(HTTPException) as removed:
            get_visible_knowledge_source(db, user_context(member), source.id)
        assert removed.value.status_code == 404

        organization.status = "disabled"
        db.commit()
        with pytest.raises(HTTPException) as disabled:
            get_visible_knowledge_source(db, user_context(owner), source.id)
        assert disabled.value.status_code == 404


def test_public_source_management_and_trusted_retrieval_are_separate(
    phase18_session,
) -> None:
    with phase18_session() as db:
        admin = create_user(db, "phase18-public-admin@example.test", role="admin")
        user = create_user(db, "phase18-public-user@example.test")
        with pytest.raises(HTTPException) as denied:
            create_knowledge_source(
                db,
                user_context(user),
                visibility="public",
                title="Untrusted public source",
                source_type="url",
            )
        assert denied.value.status_code == 403

        source = create_knowledge_source(
            db,
            user_context(admin),
            visibility="public",
            title="Curated public source",
            source_type="url",
        )
        db.commit()
        assert list_visible_knowledge_sources(db, user_context(user)) == []
        assert get_visible_knowledge_source(db, user_context(admin), source.id).id == source.id

        source.trust_state = "approved_for_rag"
        source.status = "ingested"
        db.commit()
        assert get_visible_knowledge_source(db, user_context(user), source.id).id == source.id
        trusted = db.execute(
            trusted_knowledge_sources_statement(db, user_context(user))
        ).scalars().all()
        assert [item.id for item in trusted] == [source.id]


def test_storage_key_is_derived_from_durable_lineage_and_rejects_traversal() -> None:
    source = KnowledgeSourceModel(
        id="ksrc_123",
        owner_user_id="user_123",
        organization_id=None,
        visibility="private",
        source_type="upload",
        title="Private source",
        status="registered",
        trust_state="needs_review",
    )
    document = KnowledgeDocumentModel(
        id="kdoc_123",
        knowledge_source_id=source.id,
        filename="risk.md",
        media_type="text/markdown",
        status="registered",
    )
    version = KnowledgeDocumentVersionModel(
        id="kver_123",
        document_id=document.id,
        version_number=1,
        storage_key="pending",
        size_bytes=0,
        status="pending_upload",
    )

    key = build_version_object_key(source, document, version)
    assert key == (
        "knowledge/private/user_123/sources/ksrc_123/documents/"
        "kdoc_123/versions/kver_123/original"
    )
    assert validate_knowledge_object_key(key) == key

    source.id = "../cross-tenant"
    with pytest.raises(StorageConfigurationError):
        build_version_object_key(source, document, version)
    with pytest.raises(StorageConfigurationError):
        validate_knowledge_object_key(
            "knowledge/private/user_123/sources/../../secret/documents/kdoc/versions/kver/original"
        )


def test_in_memory_private_storage_is_create_only_bounded_and_idempotently_deleted() -> None:
    storage = InMemoryPrivateObjectStorage()
    key = (
        "knowledge/public/global/sources/ksrc_1/documents/"
        "kdoc_1/versions/kver_1/original"
    )
    metadata = storage.put_create_only(
        key=key,
        content=b"controlled content",
        content_type="text/plain",
    )
    assert metadata.size_bytes == len(b"controlled content")
    assert storage.get_bounded(key=key, max_bytes=100).content == b"controlled content"
    with pytest.raises(ObjectConflictError):
        storage.put_create_only(key=key, content=b"duplicate", content_type="text/plain")
    with pytest.raises(StorageError):
        storage.get_bounded(key=key, max_bytes=1)
    with pytest.raises(StorageError):
        storage.signed_download_url(key=key, expires_in=timedelta(minutes=1))

    storage.delete(key=key)
    storage.delete(key=key)
    with pytest.raises(ObjectNotFoundError):
        storage.head(key=key)


def test_supabase_storage_uses_server_credential_without_leaking_provider_errors() -> None:
    secret = "service-role-secret-value"
    seen_requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_requests.append(request)
        if request.method == "POST":
            return httpx.Response(500, json={"message": f"provider echoed {secret}"})
        return httpx.Response(404)

    adapter = SupabasePrivateObjectStorage(
        supabase_url="https://project.supabase.co",
        service_role_key=secret,
        bucket="private-knowledge",
        timeout_seconds=1,
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    key = (
        "knowledge/private/user_1/sources/ksrc_1/documents/"
        "kdoc_1/versions/kver_1/original"
    )
    with pytest.raises(StorageError) as failed:
        adapter.put_create_only(key=key, content=b"private", content_type="text/plain")

    assert secret not in str(failed.value)
    assert len(seen_requests) == 1
    assert seen_requests[0].headers["authorization"] == f"Bearer {secret}"
    assert seen_requests[0].headers["x-upsert"] == "false"
    assert secret not in str(seen_requests[0].url)


def test_supabase_storage_stops_oversized_downloads() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            headers={"content-type": "text/plain"},
            content=b"larger than the allowed bound",
        )

    adapter = SupabasePrivateObjectStorage(
        supabase_url="https://project.supabase.co",
        service_role_key="bounded-read-secret",
        bucket="private-knowledge",
        timeout_seconds=1,
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    key = (
        "knowledge/private/user_1/sources/ksrc_1/documents/"
        "kdoc_1/versions/kver_1/original"
    )
    with pytest.raises(StorageError, match="allowed download size"):
        adapter.get_bounded(key=key, max_bytes=5)
    assert len(requests) == 1
    assert requests[0].method == "GET"


def test_private_storage_config_is_disabled_by_default_and_fails_closed() -> None:
    disabled = Settings(_env_file=None)
    assert disabled.knowledge_storage_enabled is False
    with pytest.raises(StorageConfigurationError):
        create_private_object_storage(disabled)

    with pytest.raises(ValueError, match="SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY"):
        Settings(
            _env_file=None,
            app_env="production",
            knowledge_storage_enabled=True,
            supabase_url="",
            supabase_service_role_key="",
        )
    with pytest.raises(ValueError, match="storage configuration"):
        Settings(
            _env_file=None,
            knowledge_storage_enabled=True,
            supabase_storage_bucket="../public",
        )
    with pytest.raises(ValueError, match="DOCUMENT_INGEST_ENABLED requires"):
        Settings(_env_file=None, document_ingest_enabled=True)


def test_document_ingest_registry_contract_is_exact_and_executor_is_feature_gated() -> None:
    valid_input = {"document_version_id": "kver_contract_123"}
    spec = validate_submission_schema(
        "document.ingest",
        "document.ingest.v1",
        valid_input,
    )
    assert spec.executor_name == "document_ingest"

    with pytest.raises(HTTPException) as extra_input:
        validate_submission_schema(
            "document.ingest",
            "document.ingest.v1",
            {**valid_input, "organization_id": "org_caller_scope"},
        )
    assert extra_input.value.status_code == 422

    valid_result = {
        "document_version_id": valid_input["document_version_id"],
        "content_checksum": "a" * 64,
        "chunk_count": 2,
        "embedding_count": 2,
        "parser_version": "markdown.v1",
        "chunker_version": "heading.v1",
        "embedding_model": "disabled-foundation",
    }
    validate_result_schema(
        "document.ingest",
        "document.ingest.v1",
        JobResultEnvelope(
            result_schema_version="document.ingest.v1",
            result_json=valid_result,
        ),
    )
    with pytest.raises(HTTPException) as extra_result:
        validate_result_schema(
            "document.ingest",
            "document.ingest.v1",
            JobResultEnvelope(
                result_schema_version="document.ingest.v1",
                result_json={**valid_result, "risk_rating": "low"},
            ),
        )
    assert extra_result.value.status_code == 422
    assert executor_for_job_type("document.ingest").__class__.__name__ == "DocumentIngestJobExecutor"


def test_document_ingest_submission_remains_disabled(
    phase18_session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("JOBS_ENABLED", "true")
    get_settings.cache_clear()
    with phase18_session() as db:
        user = create_user(db, "phase18-job-owner@example.test")
        actor = user_context(user)
        request = JobSubmissionRequest(
            job_type="document.ingest",
            input_schema_version="document.ingest.v1",
            input_json={"document_version_id": "kver_disabled_123"},
        )
        with pytest.raises(HTTPException) as denied:
            submit_job(db, actor, request, "phase18-disabled-ingest")
        assert denied.value.status_code == 403
