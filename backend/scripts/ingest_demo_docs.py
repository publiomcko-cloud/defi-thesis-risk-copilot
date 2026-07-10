import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.rag.ingest import ingest_knowledge_base


def main() -> int:
    records = ingest_knowledge_base()
    print(f"Ingested {len(records)} chunks into the local RAG index")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
