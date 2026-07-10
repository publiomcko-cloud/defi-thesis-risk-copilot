import json
from pathlib import Path
from typing import Any

from app.rag.chunking import TextChunk


DEFAULT_INDEX_PATH = Path(__file__).resolve().parents[2] / ".rag_index.json"


class JsonVectorStore:
    def __init__(self, path: Path = DEFAULT_INDEX_PATH) -> None:
        self.path = path

    def save(self, records: list[dict[str, Any]]) -> None:
        self.path.write_text(json.dumps(records, indent=2), encoding="utf-8")

    def load(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        return json.loads(self.path.read_text(encoding="utf-8"))


def build_record(chunk: TextChunk, embedding: dict[str, float]) -> dict[str, Any]:
    return {
        "id": chunk.id,
        "text": chunk.text,
        "metadata": chunk.metadata,
        "embedding": embedding,
    }
