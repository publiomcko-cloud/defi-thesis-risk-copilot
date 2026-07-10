from pathlib import Path

from app.rag.chunking import chunk_markdown_document
from app.rag.embeddings import LocalHashEmbeddingProvider
from app.rag.loaders import load_markdown_documents
from app.rag.vector_store import JsonVectorStore, build_record


DEFAULT_KNOWLEDGE_BASE = Path(__file__).resolve().parents[3] / "knowledge_base"


def ingest_knowledge_base(
    knowledge_base_path: Path = DEFAULT_KNOWLEDGE_BASE,
    store: JsonVectorStore | None = None,
) -> list[dict]:
    embedding_provider = LocalHashEmbeddingProvider()
    vector_store = store or JsonVectorStore()
    records = []

    for document in load_markdown_documents(knowledge_base_path):
        for chunk in chunk_markdown_document(document):
            records.append(build_record(chunk, embedding_provider.embed(chunk.text)))

    vector_store.save(records)
    return records
