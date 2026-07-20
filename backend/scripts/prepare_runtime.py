from app.core.config import get_settings
from app.db.session import SessionLocal
from app.demo.seed_data import seed_demo_data
from app.rag.ingest import ingest_knowledge_base


def main() -> int:
    settings = get_settings()
    with SessionLocal() as db:
        result = seed_demo_data(db, write_examples=not settings.public_demo_mode)
        print(f"Demo seed ready: {result.counts}")

    records = ingest_knowledge_base()
    print(f"RAG index ready with {len(records)} chunks.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
