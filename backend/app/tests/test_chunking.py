from pathlib import Path

from app.rag.chunking import chunk_markdown_document
from app.rag.loaders import LoadedDocument


def test_markdown_chunking_preserves_section_metadata() -> None:
    document = LoadedDocument(
        path=Path("knowledge_base/pendle/README.md"),
        protocol="pendle",
        title="Pendle Notes",
        source_url="knowledge_base/pendle/README.md",
        content=(
            "# Pendle Notes\n\n"
            "Intro text.\n\n"
            "## Principal Tokens\n\n"
            "A PT represents principal redeemable at maturity.\n\n"
            "## Maturity Risk\n\n"
            "Maturity risk includes exit timing and liquidity."
        ),
    )

    chunks = chunk_markdown_document(document)

    assert len(chunks) == 3
    assert chunks[1].metadata["protocol"] == "pendle"
    assert chunks[1].metadata["section_title"] == "Principal Tokens"
    assert chunks[2].metadata["risk_category"] == "liquidity"
