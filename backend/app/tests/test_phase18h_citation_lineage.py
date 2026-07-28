from app.rag.citations import results_to_sources
from app.rag.retriever import RetrievalResult


def test_durable_retrieval_lineage_is_preserved_in_report_source_data() -> None:
    result = RetrievalResult(
        chunk_id="kchunk_123",
        text="Curated protocol context",
        similarity_score=0.9,
        metadata={
            "document_title": "Curated Aave Notes",
            "section_title": "Oracle Safety",
            "protocol": "aave",
            "source_url": "knowledge_base/aave/README.md",
            "citation_lineage": {
                "citation_id": "kcite_123",
                "source_id": "ksrc_123",
                "source_title": "Curated Aave Notes",
                "document_id": "kdoc_123",
                "document_version_id": "kver_123",
                "document_version_checksum": "a" * 64,
                "chunk_id": "kchunk_123",
                "chunk_checksum": "b" * 64,
                "heading_path": ["Oracle Safety"],
            },
        },
    )

    source = results_to_sources([result])[0]

    assert source.citation_lineage is not None
    assert source.citation_lineage.document_version_id == "kver_123"
    assert source.citation_lineage.chunk_id == "kchunk_123"
    assert "storage" not in source.model_dump_json().lower()
