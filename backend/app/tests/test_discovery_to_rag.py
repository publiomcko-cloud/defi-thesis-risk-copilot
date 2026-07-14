from pathlib import Path

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.discovery.collectors import ManualDiscoveryCollector
from app.discovery.filters import passes_pool_filter, passes_protocol_filter
from app.discovery.normalizer import normalize_defillama_pool, normalize_defillama_protocol
from app.discovery.schemas import DiscoveryFilters, DiscoveryRunRequest, ManualDiscoveryItem
from app.discovery.service import run_discovery
from app.knowledge_base.ingestion_service import ingest_review_item_to_rag
from app.knowledge_base.markdown_writer import HUMAN_APPROVAL_STATEMENT, NON_ADVISORY_DISCLAIMER
from app.models.discovered_item import DiscoveredItemModel
from app.models.evaluation_result import EvaluationResultModel
from app.models.review_item import ReviewItemModel
from app.rag.ingest import ingest_knowledge_base
from app.rag.retriever import Retriever
from app.rag.vector_store import JsonVectorStore


def test_defillama_and_manual_discovery_normalization() -> None:
    protocol = normalize_defillama_protocol(
        {
            "name": "Curve",
            "slug": "curve",
            "chains": ["Ethereum"],
            "tvl": 1_000_000_000,
            "category": "Dexes",
        }
    )
    pool = normalize_defillama_pool(
        {
            "project": "pendle",
            "symbol": "PT-sUSDE",
            "chain": "Ethereum",
            "pool": "pool-1",
            "tvlUsd": 5_000_000,
        }
    )
    manual = ManualDiscoveryCollector().collect(
        [
            ManualDiscoveryItem(
                title="Derive options docs",
                url="https://docs.derive.xyz/",
                protocol="derive",
                source_type="options_docs",
            )
        ]
    )[0]

    assert protocol.protocol == "Curve"
    assert protocol.market_identifier == "defillama:protocol:curve"
    assert pool.source_type == "yield_pool"
    assert pool.protocol == "pendle"
    assert manual.source == "manual"
    assert manual.protocol == "derive"


def test_discovery_filter_behavior() -> None:
    filters = DiscoveryFilters(
        min_tvl_usd=10_000_000,
        min_pool_tvl_usd=1_000_000,
        chain_allowlist=["ethereum"],
        category_allowlist=["lending"],
        protocol_blocklist=["blocked"],
    )

    assert passes_protocol_filter(
        {"name": "Aave", "category": "Lending", "chains": ["Ethereum"], "tvl": 100_000_000},
        filters,
    )
    assert not passes_protocol_filter(
        {"name": "Blocked", "category": "Lending", "chains": ["Ethereum"], "tvl": 100_000_000},
        filters,
    )
    assert not passes_pool_filter(
        {"project": "pendle", "chain": "Ethereum", "tvlUsd": 100_000},
        filters,
    )


def test_discovery_deduplicates_and_can_call_evaluation(monkeypatch) -> None:
    db = _build_test_session()
    evaluated: list[str] = []

    def fake_evaluate(discovered_item_id: str, db):
        evaluated.append(discovered_item_id)

    monkeypatch.setattr("app.discovery.service.evaluate_discovered_item", fake_evaluate)
    request = DiscoveryRunRequest(
        include_defillama=False,
        auto_evaluate=True,
        evaluation_limit=5,
        manual_items=[
            ManualDiscoveryItem(
                title="Ethena docs",
                url="https://docs.ethena.fi/",
                protocol="ethena",
            )
        ],
    )

    first = run_discovery(request, db)
    second = run_discovery(request, db)

    assert first.created_count == 1
    assert second.created_count == 0
    assert second.duplicate_count == 1
    assert evaluated
    assert db.query(DiscoveredItemModel).count() == 1


@pytest.mark.parametrize("status", ["needs_review", "rejected", "needs_more_data", "archived"])
def test_non_approved_review_items_cannot_be_ingested(status: str, tmp_path: Path) -> None:
    db = _build_test_session()
    review = _seed_review_item(db, status=status)

    with pytest.raises(HTTPException) as exc:
        ingest_review_item_to_rag(review.id, db, knowledge_base_root=tmp_path)

    assert exc.value.status_code == 409


def test_approved_review_item_can_be_ingested_and_duplicate_is_prevented(
    tmp_path: Path,
    monkeypatch,
) -> None:
    db = _build_test_session()
    review = _seed_review_item(db, status="approved_for_rag")
    store = JsonVectorStore(tmp_path / "rag_index.json")
    refreshed: list[int] = []

    def fake_refresh(knowledge_base_path):
        records = ingest_knowledge_base(knowledge_base_path=knowledge_base_path, store=store)
        refreshed.append(len(records))
        return records

    monkeypatch.setattr("app.knowledge_base.ingestion_service.ingest_knowledge_base", fake_refresh)

    ingestion, refreshed_count = ingest_review_item_to_rag(review.id, db, knowledge_base_root=tmp_path)

    markdown = Path(ingestion.generated_markdown_path).read_text(encoding="utf-8")
    assert refreshed_count == refreshed[0]
    assert HUMAN_APPROVAL_STATEMENT in markdown
    assert NON_ADVISORY_DISCLAIMER in markdown
    assert "Risk Rating" in markdown
    assert "Missing Data" in markdown
    assert "Reviewer notes" in markdown
    assert "Source URL: https://docs.example.fi/" in markdown

    results = Retriever(store).retrieve("Example protocol oracle risk human-approved", top_k=3)
    assert results
    assert any("human-approved" in result.text for result in results)

    with pytest.raises(HTTPException) as exc:
        ingest_review_item_to_rag(review.id, db, knowledge_base_root=tmp_path)
    assert exc.value.status_code == 409


def test_rag_refresh_failure_marks_refresh_failed_and_allows_retry(
    tmp_path: Path,
    monkeypatch,
) -> None:
    db = _build_test_session()
    review = _seed_review_item(db, status="approved_for_rag")

    def failing_refresh(knowledge_base_path):
        raise RuntimeError("refresh failed")

    monkeypatch.setattr("app.knowledge_base.ingestion_service.ingest_knowledge_base", failing_refresh)

    with pytest.raises(HTTPException) as exc:
        ingest_review_item_to_rag(review.id, db, knowledge_base_root=tmp_path)

    assert exc.value.status_code == 500

    from app.models.knowledge_base_ingestion import KnowledgeBaseIngestionModel

    failed_record = db.query(KnowledgeBaseIngestionModel).filter_by(review_item_id=review.id).one()
    assert failed_record.status == "refresh_failed"

    store = JsonVectorStore(tmp_path / "rag_index_retry.json")

    def successful_refresh(knowledge_base_path):
        return ingest_knowledge_base(knowledge_base_path=knowledge_base_path, store=store)

    monkeypatch.setattr("app.knowledge_base.ingestion_service.ingest_knowledge_base", successful_refresh)

    ingestion, refreshed_count = ingest_review_item_to_rag(review.id, db, knowledge_base_root=tmp_path)

    assert ingestion.id == failed_record.id
    assert ingestion.status == "ingested"
    assert refreshed_count > 0


def _build_test_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    return Session()


def _seed_review_item(db, status: str) -> ReviewItemModel:
    discovered = DiscoveredItemModel(
        id="disc_ingest_test",
        discovery_key=f"disc_key_{status}",
        source="manual",
        source_type="documentation",
        title="Example protocol docs",
        url="https://docs.example.fi/",
        protocol="example",
        chain="ethereum",
        asset=None,
        market_identifier="manual:example-docs",
        raw_payload={
            "source_quality_notes": [
                "Candidate includes a source URL.",
                "This candidate is not trusted until human review approves it.",
            ]
        },
        status=status,
    )
    evaluation = EvaluationResultModel(
        id="eval_ingest_test",
        discovered_item_id=discovered.id,
        report_id="report_ingest_test",
        risk_rating="Moderate",
        risk_score=4,
        confidence="medium",
        risk_summary="Example protocol documentation mentions oracle risk and review uncertainty.",
        missing_data_json=["audit recency", "oracle configuration"],
        sources_json=[{"title": "Example docs", "url": "https://docs.example.fi/"}],
        report_json={
            "assumptions": [
                "Human review approval is required before ingestion.",
                "The source remains educational and non-advisory.",
            ]
        },
    )
    review = ReviewItemModel(
        id=f"review_ingest_test_{status}",
        discovered_item_id=discovered.id,
        evaluation_result_id=evaluation.id,
        status=status,
        reviewer_notes="Approved by reviewer for controlled RAG ingestion.",
        prepared_for_rag=status == "approved_for_rag",
    )
    db.add(discovered)
    db.add(evaluation)
    db.add(review)
    db.commit()
    return review
