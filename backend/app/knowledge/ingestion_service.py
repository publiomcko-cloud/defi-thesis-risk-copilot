from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.schemas import UserContext
from app.auth.service import record_audit_event
from app.core.config import get_settings
from app.jobs.control_service import submit_job
from app.jobs.schemas import JobSubmissionRequest
from app.knowledge.access import can_manage_knowledge_source, get_visible_knowledge_source
from app.models.knowledge import KnowledgeDocumentModel, KnowledgeDocumentVersionModel, KnowledgeSourceModel
from app.models.job import JobModel


def submit_document_ingestion(
    db: Session,
    actor: UserContext,
    version_id: str,
    idempotency_key: str,
):
    if not get_settings().document_ingest_enabled:
        raise HTTPException(status_code=503, detail="Document ingestion is disabled.")
    version, document, source = _load_visible_version(db, actor, version_id)
    if not can_manage_knowledge_source(db, actor, source):
        raise HTTPException(status_code=403, detail="Knowledge source manager role required")
    if source.trust_state != "approved_for_rag":
        raise HTTPException(status_code=409, detail="Knowledge source approval is required before ingestion.")
    if version.status == "ingestion_pending" and version.created_by_job_id:
        existing = db.get(JobModel, version.created_by_job_id)
        if existing is not None and existing.status not in {"completed", "failed", "cancelled", "dead_letter"}:
            if existing.idempotency_key == idempotency_key:
                return existing, True
            raise HTTPException(status_code=409, detail="Document version already has an active ingestion job.")
    if version.status not in {"uploaded", "failed", "ingestion_pending"}:
        raise HTTPException(status_code=409, detail="Document version is not ready for ingestion.")

    def mark_pending(job) -> None:
        version.created_by_job_id = job.id
        version.status = "ingestion_pending"
        if document.current_version_id is None:
            document.status = "ingestion_pending"
            source.status = "ingestion_pending"
        job.result_resource_type = "knowledge_document_version"
        job.result_resource_id = version.id
        # JSON columns do not track nested in-place mutations. Reassign the
        # snapshot so this server-derived lineage is committed with the job.
        server_context = dict(job.input_json["_server_context"])
        server_context.update(
            {
                "knowledge_source_id": source.id,
                "knowledge_document_id": document.id,
                "document_version_id": version.id,
            }
        )
        job.input_json = {**job.input_json, "_server_context": server_context}
        record_audit_event(
            db,
            actor.id,
            "knowledge.document_ingestion_submitted",
            "knowledge_document_version",
            version.id,
            {"job_id": job.id, "knowledge_source_id": source.id},
            commit=False,
        )

    return submit_job(
        db,
        actor,
        JobSubmissionRequest(
            job_type="document.ingest",
            input_schema_version="document.ingest.v1",
            input_json={"document_version_id": version.id},
            organization_id=source.organization_id,
        ),
        idempotency_key,
        allow_document_ingest=True,
        before_commit=mark_pending,
    )


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
