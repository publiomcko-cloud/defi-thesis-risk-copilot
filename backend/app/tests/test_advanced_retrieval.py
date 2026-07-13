import json
from pathlib import Path

from app.rag.citations import validate_retrieval_citations
from app.rag.evaluation import evaluate_retriever, write_default_eval_dataset
from app.rag.hybrid_retriever import HybridRetriever
from app.rag.ingest import ingest_knowledge_base
from app.rag.retriever import RetrievalResult, Retriever
from app.rag.vector_store import JsonVectorStore


def test_existing_local_retrieval_still_works(tmp_path: Path) -> None:
    store = JsonVectorStore(tmp_path / "rag_index.json")
    ingest_knowledge_base(store=store)

    results = Retriever(store).retrieve("What is Health Factor?", top_k=3)

    assert results
    assert results[0].metadata["protocol"] == "aave"


def test_hybrid_retriever_supports_metadata_filters(tmp_path: Path) -> None:
    store = JsonVectorStore(tmp_path / "rag_index.json")
    ingest_knowledge_base(store=store)

    results = HybridRetriever(store, semantic_enabled=False).retrieve(
        "What is oracle risk?",
        top_k=3,
        metadata_filters={"protocol": "chainlink"},
    )

    assert results
    assert {result.metadata["protocol"] for result in results} == {"chainlink"}
    assert "retrieval_scores" in results[0].metadata


def test_semantic_retrieval_can_be_enabled(tmp_path: Path) -> None:
    store = JsonVectorStore(tmp_path / "rag_index.json")
    ingest_knowledge_base(store=store)

    results = HybridRetriever(store, semantic_enabled=True).retrieve(
        "Explain loan to value threshold liquidation mechanics",
        top_k=3,
    )

    assert results
    assert any(result.metadata["protocol"] == "morpho" for result in results)


def test_citation_validation_reports_missing_metadata() -> None:
    issues = validate_retrieval_citations(
        [
            RetrievalResult(
                chunk_id="missing_source",
                text="test",
                metadata={"document_title": "Doc", "section_title": "Section", "protocol": "aave"},
                similarity_score=1.0,
            )
        ]
    )

    assert "missing citation metadata: source_url" in issues[0]


def test_retrieval_evaluation_records_metrics(tmp_path: Path) -> None:
    store = JsonVectorStore(tmp_path / "rag_index.json")
    ingest_knowledge_base(store=store)
    dataset_path = tmp_path / "retrieval_eval_dataset.json"
    output_path = tmp_path / "retrieval_eval_results.json"
    write_default_eval_dataset(dataset_path)

    summary = evaluate_retriever(
        retriever_name="hybrid_semantic",
        dataset_path=dataset_path,
        output_path=output_path,
        top_k=3,
        store=store,
    )

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert summary.total_cases == 6
    assert payload["total_cases"] == 6
    assert "pass_rate" in payload
