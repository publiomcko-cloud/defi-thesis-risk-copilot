from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.discovery.schemas import DiscoveredKnowledgeBaseResponse
from app.knowledge_base.ingestion_service import list_discovered_knowledge_base_ingestions

router = APIRouter(tags=["knowledge-base"])


@router.get("/knowledge-base/discovered", response_model=DiscoveredKnowledgeBaseResponse)
def get_discovered_knowledge_base_items(
    protocol: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> DiscoveredKnowledgeBaseResponse:
    return DiscoveredKnowledgeBaseResponse(
        items=list_discovered_knowledge_base_ingestions(
            db,
            protocol=protocol,
            limit=limit,
        )
    )
