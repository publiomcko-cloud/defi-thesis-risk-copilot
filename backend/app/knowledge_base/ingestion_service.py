from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.discovery.schemas import KnowledgeBaseIngestionRecord
from app.knowledge_base.markdown_writer import write_discovered_markdown
from app.models.discovered_item import DiscoveredItemModel
from app.models.evaluation_result import EvaluationResultModel
from app.models.knowledge_base_ingestion import KnowledgeBaseIngestionModel
from app.models.review_item import ReviewItemModel
from app.rag.ingest import DEFAULT_KNOWLEDGE_BASE, ingest_knowledge_base


ELIGIBLE_STATUS = "approved_for_rag"


def ingest_review_item_to_rag(
    review_item_id: str,
    db: Session,
    knowledge_base_root: Path = DEFAULT_KNOWLEDGE_BASE,
    ingested_by: str = "system",
) -> tuple[KnowledgeBaseIngestionRecord, int]:
    existing = db.execute(
        select(KnowledgeBaseIngestionModel).where(
            KnowledgeBaseIngestionModel.review_item_id == review_item_id
        )
    ).scalars().first()
    if existing is not None:
        raise HTTPException(status_code=409, detail="Review item has already been ingested into RAG")

    review_item = db.get(ReviewItemModel, review_item_id)
    if review_item is None:
        raise HTTPException(status_code=404, detail="Review item not found")
    if review_item.status != ELIGIBLE_STATUS:
        raise HTTPException(
            status_code=409,
            detail="Only approved_for_rag review items can be ingested into RAG",
        )

    discovered_item = db.get(DiscoveredItemModel, review_item.discovered_item_id)
    evaluation_result = db.get(EvaluationResultModel, review_item.evaluation_result_id)
    if discovered_item is None or evaluation_result is None:
        raise HTTPException(status_code=500, detail="Review item is missing discovery or evaluation data")

    markdown_path = write_discovered_markdown(
        knowledge_base_root,
        discovered_item,
        review_item,
        evaluation_result,
    )
    record = KnowledgeBaseIngestionModel(
        id=f"kbi_{uuid4().hex[:12]}",
        review_item_id=review_item.id,
        generated_markdown_path=str(markdown_path),
        ingested_at=datetime.now(UTC),
        ingested_by=ingested_by,
        source_url=discovered_item.url,
        protocol=discovered_item.protocol,
        status="ingested",
    )
    db.add(record)
    db.commit()
    refreshed_records = ingest_knowledge_base(knowledge_base_path=knowledge_base_root)
    db.refresh(record)
    return _record_schema(record), len(refreshed_records)


def list_discovered_knowledge_base_ingestions(
    db: Session,
    protocol: str | None = None,
    limit: int = 100,
) -> list[KnowledgeBaseIngestionRecord]:
    statement = select(KnowledgeBaseIngestionModel).order_by(
        KnowledgeBaseIngestionModel.ingested_at.desc()
    )
    if protocol:
        statement = statement.where(KnowledgeBaseIngestionModel.protocol == protocol.lower())
    return [_record_schema(record) for record in db.execute(statement.limit(limit)).scalars().all()]


def _record_schema(record: KnowledgeBaseIngestionModel) -> KnowledgeBaseIngestionRecord:
    return KnowledgeBaseIngestionRecord(
        id=record.id,
        review_item_id=record.review_item_id,
        generated_markdown_path=record.generated_markdown_path,
        ingested_at=record.ingested_at,
        ingested_by=record.ingested_by,
        source_url=record.source_url,
        protocol=record.protocol,
        status=record.status,
    )
