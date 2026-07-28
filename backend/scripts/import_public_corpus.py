"""Explicit operator command for a reversible Phase 18G curated-corpus import."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.db.session import SessionLocal
from app.knowledge.public_corpus import (
    import_curated_public_corpus,
    import_curated_public_corpus_operator,
    require_public_corpus_import_enabled,
)
from app.storage.factory import create_private_object_storage
from app.storage.memory import InMemoryPrivateObjectStorage


def main() -> int:
    parser = argparse.ArgumentParser(description="Import repository curated Markdown into durable public RAG.")
    parser.add_argument("--apply", action="store_true", help="Write private objects and durable database rows.")
    args = parser.parse_args()
    if args.apply:
        require_public_corpus_import_enabled()
        storage = create_private_object_storage()
    else:
        # The dry run intentionally performs no object writes and therefore
        # works without a configured private bucket or service-role credential.
        storage = InMemoryPrivateObjectStorage()
    with SessionLocal() as db:
        summary = (
            import_curated_public_corpus_operator(db, storage)
            if args.apply
            else import_curated_public_corpus(db, storage, dry_run=True)
        )
    print(
        f"curated public corpus: seen={summary.documents_seen} created={summary.documents_created} "
        f"unchanged={summary.documents_unchanged} versions={summary.document_versions_created} "
        f"chunks={summary.chunks_created} dry_run={summary.dry_run}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
