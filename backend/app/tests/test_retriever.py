from pathlib import Path

from app.rag.ingest import ingest_knowledge_base
from app.rag.retriever import Retriever
from app.rag.vector_store import JsonVectorStore


def test_retriever_returns_relevant_protocol_chunk(tmp_path: Path) -> None:
    store = JsonVectorStore(tmp_path / "rag_index.json")
    ingest_knowledge_base(store=store)

    results = Retriever(store).retrieve("What is LLTV in Morpho?", top_k=3)

    assert results
    assert results[0].metadata["protocol"] == "morpho"
    assert "LLTV" in results[0].text


def test_retriever_includes_source_metadata(tmp_path: Path) -> None:
    store = JsonVectorStore(tmp_path / "rag_index.json")
    ingest_knowledge_base(store=store)

    results = Retriever(store).retrieve("What is oracle risk?", top_k=3)

    assert results
    assert "source_url" in results[0].metadata
    assert "section_title" in results[0].metadata
    assert results[0].similarity_score > 0
