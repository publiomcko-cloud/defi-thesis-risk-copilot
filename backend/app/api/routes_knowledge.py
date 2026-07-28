from fastapi import APIRouter, Depends, File, Form, Header, Request, UploadFile
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.auth.dependencies import require_admin, require_authenticated_user
from app.core.config import get_settings
from app.auth.schemas import UserContext
from app.db.session import get_db
from app.knowledge.schemas import (
    KnowledgeDocumentResponse,
    KnowledgeDocumentsResponse,
    KnowledgeDocumentRollbackRequest,
    KnowledgeDocumentVersionResponse,
    KnowledgeEmbeddingPromotionRequest,
    KnowledgeSourceCreateRequest,
    KnowledgeSourceResponse,
    KnowledgeSourcesResponse,
    KnowledgeSourceUpdateRequest,
    KnowledgeReadinessResponse,
    ShadowRetrievalRequest,
    ShadowRetrievalResponse,
)
from app.knowledge.service import (
    create_document_upload,
    create_document_version_upload,
    create_source,
    delete_document,
    delete_source,
    get_document,
    get_source,
    list_sources,
    list_source_documents,
    knowledge_document_version_response,
    update_source,
)
from app.knowledge.ingestion_service import submit_document_ingestion
from app.knowledge.embedding_service import submit_document_embedding
from app.knowledge.lifecycle_service import (
    promote_document_embedding_generation,
    rollback_document_version,
)
from app.knowledge.shadow_retriever import retrieve_shadow_knowledge
from app.models.knowledge import (
    KnowledgeChunkEmbeddingModel,
    KnowledgeCleanupTaskModel,
    KnowledgeDocumentModel,
    KnowledgeDocumentVersionModel,
    KnowledgeSourceModel,
)
from app.rag.vector_store import JsonVectorStore
from app.jobs.control_service import job_response
from app.jobs.schemas import JobSubmissionResponse


router = APIRouter(tags=["knowledge"])


@router.get("/knowledge/sources", response_model=KnowledgeSourcesResponse)
def get_knowledge_sources(
    db: Session = Depends(get_db),
    actor: UserContext = Depends(require_authenticated_user),
) -> KnowledgeSourcesResponse:
    return KnowledgeSourcesResponse(items=list_sources(db, actor))


@router.post("/knowledge/sources", response_model=KnowledgeSourceResponse)
def post_knowledge_source(
    request: KnowledgeSourceCreateRequest,
    db: Session = Depends(get_db),
    actor: UserContext = Depends(require_authenticated_user),
) -> KnowledgeSourceResponse:
    return create_source(db, actor, request)


@router.get("/knowledge/sources/{source_id}", response_model=KnowledgeSourceResponse)
def get_knowledge_source(
    source_id: str,
    db: Session = Depends(get_db),
    actor: UserContext = Depends(require_authenticated_user),
) -> KnowledgeSourceResponse:
    return get_source(db, actor, source_id)


@router.get(
    "/knowledge/sources/{source_id}/documents",
    response_model=KnowledgeDocumentsResponse,
)
def get_knowledge_source_documents(
    source_id: str,
    db: Session = Depends(get_db),
    actor: UserContext = Depends(require_authenticated_user),
) -> KnowledgeDocumentsResponse:
    return KnowledgeDocumentsResponse(items=list_source_documents(db, actor, source_id))


@router.patch("/knowledge/sources/{source_id}", response_model=KnowledgeSourceResponse)
def patch_knowledge_source(
    source_id: str,
    request: KnowledgeSourceUpdateRequest,
    db: Session = Depends(get_db),
    actor: UserContext = Depends(require_authenticated_user),
) -> KnowledgeSourceResponse:
    return update_source(db, actor, source_id, request)


@router.delete("/knowledge/sources/{source_id}", response_model=KnowledgeSourceResponse)
def delete_knowledge_source(
    source_id: str,
    db: Session = Depends(get_db),
    actor: UserContext = Depends(require_authenticated_user),
) -> KnowledgeSourceResponse:
    return delete_source(db, actor, source_id)


@router.post(
    "/knowledge/sources/{source_id}/documents",
    response_model=KnowledgeDocumentResponse,
)
async def post_knowledge_document(
    source_id: str,
    file: UploadFile = File(...),
    checksum: str | None = Form(default=None),
    db: Session = Depends(get_db),
    actor: UserContext = Depends(require_authenticated_user),
) -> KnowledgeDocumentResponse:
    return await create_document_upload(db, actor, source_id, file, checksum)


@router.get("/knowledge/documents/{document_id}", response_model=KnowledgeDocumentResponse)
def get_knowledge_document(
    document_id: str,
    db: Session = Depends(get_db),
    actor: UserContext = Depends(require_authenticated_user),
) -> KnowledgeDocumentResponse:
    return get_document(db, actor, document_id)


@router.delete("/knowledge/documents/{document_id}", response_model=KnowledgeDocumentResponse)
def delete_knowledge_document(
    document_id: str,
    db: Session = Depends(get_db),
    actor: UserContext = Depends(require_authenticated_user),
) -> KnowledgeDocumentResponse:
    return delete_document(db, actor, document_id)


@router.post(
    "/knowledge/documents/{document_id}/versions",
    response_model=KnowledgeDocumentResponse,
)
async def post_knowledge_document_version(
    document_id: str,
    file: UploadFile = File(...),
    checksum: str | None = Form(default=None),
    db: Session = Depends(get_db),
    actor: UserContext = Depends(require_authenticated_user),
) -> KnowledgeDocumentResponse:
    return await create_document_version_upload(db, actor, document_id, file, checksum)


@router.post(
    "/knowledge/document-versions/{version_id}/ingest",
    response_model=JobSubmissionResponse,
    status_code=202,
)
def post_knowledge_document_ingestion(
    version_id: str,
    db: Session = Depends(get_db),
    actor: UserContext = Depends(require_authenticated_user),
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
) -> JobSubmissionResponse:
    job, replayed = submit_document_ingestion(db, actor, version_id, idempotency_key)
    return JobSubmissionResponse(job=job_response(job), idempotent_replay=replayed)


@router.post(
    "/knowledge/document-versions/{version_id}/embed",
    response_model=JobSubmissionResponse,
    status_code=202,
)
def post_knowledge_document_embedding(
    version_id: str,
    db: Session = Depends(get_db),
    actor: UserContext = Depends(require_authenticated_user),
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
) -> JobSubmissionResponse:
    job, replayed = submit_document_embedding(db, actor, version_id, idempotency_key)
    return JobSubmissionResponse(job=job_response(job), idempotent_replay=replayed)


@router.post(
    "/knowledge/documents/{document_id}/rollback",
    response_model=KnowledgeDocumentResponse,
)
def post_knowledge_document_rollback(
    document_id: str,
    payload: KnowledgeDocumentRollbackRequest,
    db: Session = Depends(get_db),
    actor: UserContext = Depends(require_authenticated_user),
) -> KnowledgeDocumentResponse:
    document = rollback_document_version(db, actor, document_id, payload.version_id)
    return get_document(db, actor, document.id)


@router.post(
    "/knowledge/document-versions/{version_id}/embedding-generations/promote",
    response_model=KnowledgeDocumentVersionResponse,
)
def post_knowledge_embedding_promotion(
    version_id: str,
    payload: KnowledgeEmbeddingPromotionRequest,
    db: Session = Depends(get_db),
    actor: UserContext = Depends(require_authenticated_user),
) -> KnowledgeDocumentVersionResponse:
    version = promote_document_embedding_generation(
        db, actor, version_id, payload.embedding_generation_id
    )
    return knowledge_document_version_response(version)


@router.post(
    "/knowledge/shadow-retrieval",
    response_model=ShadowRetrievalResponse,
)
def post_knowledge_shadow_retrieval(
    payload: ShadowRetrievalRequest,
    request: Request,
    db: Session = Depends(get_db),
    actor: UserContext = Depends(require_authenticated_user),
) -> ShadowRetrievalResponse:
    result = retrieve_shadow_knowledge(
        db,
        actor,
        query=payload.query,
        top_k=payload.top_k,
        protocols=payload.protocols,
        request_id=request.state.request_id,
    )
    db.commit()
    return result


@router.get("/knowledge/readiness", response_model=KnowledgeReadinessResponse)
def get_knowledge_readiness(
    db: Session = Depends(get_db),
    _: UserContext = Depends(require_admin),
) -> KnowledgeReadinessResponse:
    """Safe aggregate readiness evidence for administrators only.

    This intentionally excludes private object keys, bucket names, source
    contents, provider errors, and all credential material.
    """

    settings = get_settings()
    database_ready = True
    pgvector_ready = False
    try:
        db.execute(text("select 1"))
        if db.bind is not None and db.bind.dialect.name == "postgresql":
            pgvector_ready = bool(
                db.execute(text("SELECT 1 FROM pg_extension WHERE extname = 'vector'")).scalar()
            )
    except Exception:
        database_ready = False

    def count(statement) -> int:
        if not database_ready:
            return 0
        return int(db.execute(statement).scalar_one())

    return KnowledgeReadinessResponse(
        database_ready=database_ready,
        pgvector_ready=pgvector_ready,
        json_fallback_ready=JsonVectorStore().path.exists(),
        storage_enabled=settings.knowledge_storage_enabled,
        document_ingest_enabled=settings.document_ingest_enabled,
        embeddings_enabled=settings.knowledge_embeddings_enabled,
        shadow_retrieval_enabled=settings.knowledge_shadow_retrieval_enabled,
        public_corpus_import_enabled=settings.knowledge_public_corpus_import_enabled,
        pgvector_primary_enabled=settings.knowledge_pgvector_primary_enabled,
        visible_source_count=count(select(func.count()).select_from(KnowledgeSourceModel).where(KnowledgeSourceModel.deleted_at.is_(None))),
        ready_document_count=count(select(func.count()).select_from(KnowledgeDocumentModel).where(KnowledgeDocumentModel.status == "ready").where(KnowledgeDocumentModel.deleted_at.is_(None))),
        ready_version_count=count(select(func.count()).select_from(KnowledgeDocumentVersionModel).where(KnowledgeDocumentVersionModel.status == "ready").where(KnowledgeDocumentVersionModel.deleted_at.is_(None))),
        active_embedding_count=count(select(func.count()).select_from(KnowledgeChunkEmbeddingModel).where(KnowledgeChunkEmbeddingModel.status == "completed").where(KnowledgeChunkEmbeddingModel.deleted_at.is_(None))),
        pending_cleanup_count=count(select(func.count()).select_from(KnowledgeCleanupTaskModel).where(KnowledgeCleanupTaskModel.status.in_(("pending", "failed")))),
    )
