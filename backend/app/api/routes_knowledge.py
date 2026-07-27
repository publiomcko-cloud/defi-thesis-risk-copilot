from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from app.auth.dependencies import require_authenticated_user
from app.auth.schemas import UserContext
from app.db.session import get_db
from app.knowledge.schemas import (
    KnowledgeDocumentResponse,
    KnowledgeSourceCreateRequest,
    KnowledgeSourceResponse,
    KnowledgeSourcesResponse,
    KnowledgeSourceUpdateRequest,
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
    update_source,
)


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
