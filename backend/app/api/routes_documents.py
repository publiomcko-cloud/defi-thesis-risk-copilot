from uuid import uuid4

from fastapi import APIRouter

from app.schemas.documents import DocumentIngestRequest, DocumentIngestResponse

router = APIRouter(tags=["documents"])


@router.post("/documents/ingest", response_model=DocumentIngestResponse)
def ingest_document(request: DocumentIngestRequest) -> DocumentIngestResponse:
    protocol = request.protocol.lower()
    return DocumentIngestResponse(
        status="queued",
        document_id=f"doc_{protocol}_{uuid4().hex[:10]}",
        message=(
            "Document ingestion is queued as a Phase 2 mock. "
            "Real loading, chunking, embeddings, and vector storage arrive in later phases."
        ),
    )
