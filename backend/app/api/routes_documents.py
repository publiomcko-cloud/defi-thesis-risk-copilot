from fastapi import APIRouter, Depends

from app.auth.dependencies import require_admin
from app.auth.schemas import UserContext
from app.rag.ingest import ingest_knowledge_base
from app.schemas.documents import DocumentIngestRequest, DocumentIngestResponse

router = APIRouter(tags=["documents"])


@router.post(
    "/documents/ingest",
    response_model=DocumentIngestResponse,
)
def ingest_document(
    request: DocumentIngestRequest,
    _: UserContext = Depends(require_admin),
) -> DocumentIngestResponse:
    protocol = request.protocol.lower()
    records = ingest_knowledge_base()
    matched_chunks = [
        record
        for record in records
        if record["metadata"]["protocol"].lower() == protocol
    ]
    return DocumentIngestResponse(
        status="queued",
        document_id=f"local_rag_{protocol}",
        message=(
            "Placeholder endpoint refreshed the local curated RAG index from "
            f"`knowledge_base/`. Matched {len(matched_chunks)} chunks for protocol "
            f"`{protocol}`. The request body is not yet used for arbitrary document upload."
        ),
    )
