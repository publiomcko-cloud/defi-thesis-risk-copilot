"""Version rollback, embedding selection, and bounded tombstone cleanup."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.auth.schemas import UserContext
from app.auth.service import record_audit_event
from app.knowledge.access import can_manage_knowledge_source, get_visible_knowledge_source
from app.models.knowledge import (
    KnowledgeChunkEmbeddingModel,
    KnowledgeChunkModel,
    KnowledgeCleanupTaskModel,
    KnowledgeDocumentModel,
    KnowledgeDocumentVersionModel,
    KnowledgeEmbeddingGenerationModel,
    KnowledgeEmbeddingProfileModel,
    KnowledgeSourceModel,
)
from app.storage.base import StorageConfigurationError, StorageError
from app.storage.factory import create_private_object_storage


def rollback_document_version(
    db: Session,
    actor: UserContext,
    document_id: str,
    target_version_id: str,
) -> KnowledgeDocumentModel:
    document, source = _load_manageable_document(db, actor, document_id)
    target = db.execute(
        select(KnowledgeDocumentVersionModel)
        .where(KnowledgeDocumentVersionModel.id == target_version_id)
        .where(KnowledgeDocumentVersionModel.document_id == document.id)
        .where(KnowledgeDocumentVersionModel.deleted_at.is_(None))
        .with_for_update()
    ).scalars().one_or_none()
    if target is None:
        raise HTTPException(status_code=404, detail="Knowledge document version not found")
    if target.status not in {"ready", "superseded"}:
        raise HTTPException(status_code=409, detail="Knowledge document version is not rollback-ready")
    if document.current_version_id == target.id:
        return document

    now = datetime.now(UTC)
    previous = (
        db.execute(
            select(KnowledgeDocumentVersionModel)
            .where(KnowledgeDocumentVersionModel.id == document.current_version_id)
            .with_for_update()
        ).scalars().one_or_none()
        if document.current_version_id
        else None
    )
    if previous is not None and previous.status == "ready":
        previous.status = "superseded"
        previous.superseded_at = now
    target.status = "ready"
    target.superseded_at = None
    document.current_version_id = target.id
    document.status = "ready"
    document.updated_at = now
    source.status = "ingested"
    source.updated_at = now
    record_audit_event(
        db,
        actor.id,
        "knowledge.document_version_rolled_back",
        "knowledge_document",
        document.id,
        {"from_version_id": previous.id if previous else None, "to_version_id": target.id},
        commit=False,
    )
    db.commit()
    db.refresh(document)
    return document


def promote_document_embedding_generation(
    db: Session,
    actor: UserContext,
    version_id: str,
    generation_id: str,
) -> KnowledgeDocumentVersionModel:
    version, document, source = _load_manageable_version(db, actor, version_id)
    generation = db.execute(
        select(KnowledgeEmbeddingGenerationModel)
        .where(KnowledgeEmbeddingGenerationModel.id == generation_id)
        .where(KnowledgeEmbeddingGenerationModel.document_version_id == version.id)
        .where(KnowledgeEmbeddingGenerationModel.status == "completed")
        .where(KnowledgeEmbeddingGenerationModel.deleted_at.is_(None))
        .with_for_update()
    ).scalars().one_or_none()
    if generation is None:
        raise HTTPException(status_code=404, detail="Completed embedding generation not found")
    profile = db.execute(
        select(KnowledgeEmbeddingProfileModel)
        .where(KnowledgeEmbeddingProfileModel.id == generation.embedding_profile_id)
        .where(KnowledgeEmbeddingProfileModel.status == "active")
        .with_for_update()
    ).scalars().one_or_none()
    if profile is None:
        raise HTTPException(status_code=409, detail="Embedding profile is not promotion-ready")
    embeddings = db.execute(
        select(KnowledgeChunkEmbeddingModel)
        .where(KnowledgeChunkEmbeddingModel.embedding_generation_id == generation.id)
        .where(KnowledgeChunkEmbeddingModel.embedding_profile_id == profile.id)
        .where(KnowledgeChunkEmbeddingModel.status == "completed")
        .where(KnowledgeChunkEmbeddingModel.deleted_at.is_(None))
    ).scalars().all()
    if len(embeddings) != generation.expected_chunk_count or not embeddings:
        raise HTTPException(status_code=409, detail="Embedding generation is incomplete")
    previous_profile_id = version.active_embedding_profile_id
    version.active_embedding_profile_id = profile.id
    version.embedding_model = profile.model
    version.embedding_dimensions = profile.dimensions
    record_audit_event(
        db,
        actor.id,
        "knowledge.embedding_generation_promoted",
        "knowledge_document_version",
        version.id,
        {
            "embedding_generation_id": generation.id,
            "from_profile_id": previous_profile_id,
            "to_profile_id": profile.id,
        },
        commit=False,
    )
    db.commit()
    db.refresh(version)
    return version


def schedule_version_cleanup(
    db: Session,
    version: KnowledgeDocumentVersionModel,
    *,
    now: datetime,
) -> KnowledgeCleanupTaskModel:
    task = db.execute(
        select(KnowledgeCleanupTaskModel)
        .where(KnowledgeCleanupTaskModel.document_version_id == version.id)
        .with_for_update()
    ).scalars().one_or_none()
    if task is not None:
        return task
    task = KnowledgeCleanupTaskModel(
        id=f"kclean_{uuid4().hex[:12]}",
        document_version_id=version.id,
        status="pending",
        attempt_count=0,
        requested_at=now,
        next_attempt_at=now,
    )
    db.add(task)
    return task


def cleanup_tombstoned_knowledge(
    db: Session,
    *,
    dry_run: bool,
    limit: int = 100,
) -> dict[str, int]:
    """Delete private originals and derived content only after DB revocation.

    A failed storage delete leaves the task retryable.  The task stores no
    object key, and retrieval remains blocked by the original tombstone.
    """

    now = datetime.now(UTC)
    tasks = db.execute(
        select(KnowledgeCleanupTaskModel, KnowledgeDocumentVersionModel)
        .join(
            KnowledgeDocumentVersionModel,
            KnowledgeDocumentVersionModel.id == KnowledgeCleanupTaskModel.document_version_id,
        )
        .where(KnowledgeCleanupTaskModel.status.in_({"pending", "failed"}))
        .where(KnowledgeCleanupTaskModel.next_attempt_at <= now)
        .where(KnowledgeDocumentVersionModel.deleted_at.is_not(None))
        .order_by(KnowledgeCleanupTaskModel.requested_at, KnowledgeCleanupTaskModel.id)
        .limit(limit)
        .with_for_update(skip_locked=True)
    ).all()
    counts = {"eligible": len(tasks), "completed": 0, "failed": 0, "storage_unavailable": 0}
    if dry_run or not tasks:
        return counts
    try:
        storage = create_private_object_storage()
    except StorageConfigurationError:
        counts["storage_unavailable"] = len(tasks)
        return counts

    for task, version in tasks:
        task.status = "processing"
        task.attempt_count += 1
        try:
            storage.delete(key=version.storage_key)
            _delete_derived_version_content(db, version.id)
            task.status = "completed"
            task.last_error_code = None
            task.completed_at = now
            counts["completed"] += 1
        except StorageError:
            task.status = "failed"
            task.last_error_code = "storage_delete_failed"
            task.next_attempt_at = now
            counts["failed"] += 1
    return counts


def _delete_derived_version_content(db: Session, version_id: str) -> None:
    chunk_ids = select(KnowledgeChunkModel.id).where(
        KnowledgeChunkModel.document_version_id == version_id
    )
    db.execute(
        delete(KnowledgeChunkEmbeddingModel).where(
            KnowledgeChunkEmbeddingModel.knowledge_chunk_id.in_(chunk_ids)
        )
    )
    db.execute(
        delete(KnowledgeEmbeddingGenerationModel).where(
            KnowledgeEmbeddingGenerationModel.document_version_id == version_id
        )
    )
    db.execute(delete(KnowledgeChunkModel).where(KnowledgeChunkModel.document_version_id == version_id))


def _load_manageable_document(
    db: Session,
    actor: UserContext,
    document_id: str,
) -> tuple[KnowledgeDocumentModel, KnowledgeSourceModel]:
    row = db.execute(
        select(KnowledgeDocumentModel, KnowledgeSourceModel)
        .join(KnowledgeSourceModel, KnowledgeSourceModel.id == KnowledgeDocumentModel.knowledge_source_id)
        .where(KnowledgeDocumentModel.id == document_id)
        .where(KnowledgeDocumentModel.deleted_at.is_(None))
        .where(KnowledgeSourceModel.deleted_at.is_(None))
        .with_for_update()
    ).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Knowledge document not found")
    document, source = row
    get_visible_knowledge_source(db, actor, source.id)
    if not can_manage_knowledge_source(db, actor, source):
        raise HTTPException(status_code=403, detail="Knowledge source manager role required")
    return document, source


def _load_manageable_version(
    db: Session,
    actor: UserContext,
    version_id: str,
) -> tuple[KnowledgeDocumentVersionModel, KnowledgeDocumentModel, KnowledgeSourceModel]:
    row = db.execute(
        select(KnowledgeDocumentVersionModel, KnowledgeDocumentModel, KnowledgeSourceModel)
        .join(KnowledgeDocumentModel, KnowledgeDocumentModel.id == KnowledgeDocumentVersionModel.document_id)
        .join(KnowledgeSourceModel, KnowledgeSourceModel.id == KnowledgeDocumentModel.knowledge_source_id)
        .where(KnowledgeDocumentVersionModel.id == version_id)
        .where(KnowledgeDocumentVersionModel.deleted_at.is_(None))
        .where(KnowledgeDocumentModel.deleted_at.is_(None))
        .where(KnowledgeSourceModel.deleted_at.is_(None))
        .with_for_update()
    ).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Knowledge document version not found")
    version, document, source = row
    get_visible_knowledge_source(db, actor, source.id)
    if not can_manage_knowledge_source(db, actor, source):
        raise HTTPException(status_code=403, detail="Knowledge source manager role required")
    return version, document, source
