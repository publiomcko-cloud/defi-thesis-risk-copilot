from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.schemas import UserContext
from app.auth.service import record_audit_event
from app.core.config import get_settings
from app.jobs.control_service import submit_job
from app.jobs.schemas import JobSubmissionRequest
from app.knowledge.access import can_manage_knowledge_source, get_visible_knowledge_source
from app.knowledge.embedding import (
    LOCAL_EMBEDDING_DIMENSIONS,
    LOCAL_EMBEDDING_MODEL,
    LOCAL_EMBEDDING_PROVIDER,
)
from app.models.job import JobModel
from app.models.knowledge import (
    KnowledgeDocumentModel,
    KnowledgeDocumentVersionModel,
    KnowledgeEmbeddingGenerationModel,
    KnowledgeEmbeddingProfileModel,
    KnowledgeSourceModel,
)


def submit_document_embedding(
    db: Session,
    actor: UserContext,
    version_id: str,
    idempotency_key: str,
):
    if not get_settings().knowledge_embeddings_enabled:
        raise HTTPException(status_code=503, detail="Knowledge embeddings are disabled.")
    version, document, source = _load_visible_version(db, actor, version_id)
    if not can_manage_knowledge_source(db, actor, source):
        raise HTTPException(status_code=403, detail="Knowledge source manager role required")
    if source.trust_state != "approved_for_rag" or version.status != "ready":
        raise HTTPException(status_code=409, detail="An approved ready document version is required for embedding.")
    profile = get_configured_embedding_profile(db, create=True)
    active_generation = db.execute(
        select(KnowledgeEmbeddingGenerationModel)
        .where(KnowledgeEmbeddingGenerationModel.document_version_id == version.id)
        .where(KnowledgeEmbeddingGenerationModel.embedding_profile_id == profile.id)
        .where(KnowledgeEmbeddingGenerationModel.status.in_({"pending", "processing"}))
        .where(KnowledgeEmbeddingGenerationModel.deleted_at.is_(None))
        .order_by(KnowledgeEmbeddingGenerationModel.created_at.desc())
        .with_for_update()
    ).scalars().one_or_none()
    if active_generation is not None and active_generation.created_by_job_id:
        existing = db.get(JobModel, active_generation.created_by_job_id)
        if existing is not None and existing.status not in {"completed", "failed", "cancelled", "dead_letter"}:
            if existing.idempotency_key == idempotency_key:
                return existing, True
            raise HTTPException(status_code=409, detail="Document version already has an active embedding job.")
    # A completed generation is immutable evidence and remains available for
    # rollback. Each new embedding request therefore receives a fresh
    # generation even when it uses the same reusable profile.
    generation = KnowledgeEmbeddingGenerationModel(
        id=f"kembgen_{uuid4().hex[:12]}",
        document_version_id=version.id,
        embedding_profile_id=profile.id,
        status="pending",
        created_at=datetime.now(UTC),
    )
    db.add(generation)
    db.flush()

    def mark_pending(job: JobModel) -> None:
        generation.created_by_job_id = job.id
        generation.status = "pending"
        generation.completed_chunk_count = 0
        generation.completed_at = None
        job.result_resource_type = "knowledge_embedding_generation"
        job.result_resource_id = generation.id
        context = dict(job.input_json["_server_context"])
        context.update(
            {
                "knowledge_source_id": source.id,
                "knowledge_document_id": document.id,
                "document_version_id": version.id,
                "embedding_profile_id": profile.id,
                "embedding_generation_id": generation.id,
            }
        )
        job.input_json = {**job.input_json, "_server_context": context}
        record_audit_event(
            db,
            actor.id,
            "knowledge.embedding_submitted",
            "knowledge_embedding_generation",
            generation.id,
            {"job_id": job.id, "document_version_id": version.id, "embedding_profile_id": profile.id},
            commit=False,
        )

    return submit_job(
        db,
        actor,
        JobSubmissionRequest(
            job_type="document.embed",
            input_schema_version="document.embed.v1",
            input_json={"document_version_id": version.id, "embedding_profile_id": profile.id},
            organization_id=source.organization_id,
        ),
        idempotency_key,
        allow_document_embedding=True,
        before_commit=mark_pending,
    )


def get_configured_embedding_profile(db: Session, *, create: bool) -> KnowledgeEmbeddingProfileModel:
    settings = get_settings()
    profile = db.execute(
        select(KnowledgeEmbeddingProfileModel)
        .where(KnowledgeEmbeddingProfileModel.id == settings.knowledge_embedding_profile_id)
        .with_for_update()
    ).scalars().one_or_none()
    if profile is None:
        if not create:
            raise HTTPException(status_code=409, detail="Configured embedding profile is unavailable.")
        active_profile = db.execute(
            select(KnowledgeEmbeddingProfileModel)
            .where(KnowledgeEmbeddingProfileModel.is_active.is_(True))
            .where(KnowledgeEmbeddingProfileModel.status == "active")
            .with_for_update()
        ).scalars().one_or_none()
        if active_profile is not None:
            raise HTTPException(status_code=409, detail="Configured embedding profile is unavailable.")
        profile = KnowledgeEmbeddingProfileModel(
            id=settings.knowledge_embedding_profile_id,
            provider=LOCAL_EMBEDDING_PROVIDER,
            model=LOCAL_EMBEDDING_MODEL,
            dimensions=LOCAL_EMBEDDING_DIMENSIONS,
            status="active",
            is_active=True,
            created_at=datetime.now(UTC),
        )
        db.add(profile)
        db.flush()
    if (
        profile.provider != settings.knowledge_embedding_provider
        or profile.model != settings.knowledge_embedding_model
        or profile.dimensions != settings.knowledge_embedding_dimensions
        or profile.status != "active"
        or not profile.is_active
    ):
        raise HTTPException(status_code=409, detail="Configured embedding profile is not active or compatible.")
    return profile


def _load_visible_version(db: Session, actor: UserContext, version_id: str):
    row = db.execute(
        select(KnowledgeDocumentVersionModel, KnowledgeDocumentModel, KnowledgeSourceModel)
        .join(KnowledgeDocumentModel, KnowledgeDocumentModel.id == KnowledgeDocumentVersionModel.document_id)
        .join(KnowledgeSourceModel, KnowledgeSourceModel.id == KnowledgeDocumentModel.knowledge_source_id)
        .where(KnowledgeDocumentVersionModel.id == version_id)
        .where(KnowledgeDocumentVersionModel.deleted_at.is_(None))
        .with_for_update()
    ).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Knowledge document version not found")
    version, document, source = row
    get_visible_knowledge_source(db, actor, source.id)
    if document.deleted_at is not None or source.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Knowledge document version not found")
    return version, document, source
