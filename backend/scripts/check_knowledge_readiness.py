"""Safe Phase 18 deployment readiness checks with an optional storage probe.

The default inspection does not contact object storage.  ``--probe-storage`` is
an explicit synthetic-object round trip for a configured private bucket and
deletes the object in a ``finally`` block.  No credential, bucket name, or
derived object key is printed.
"""

from __future__ import annotations

import argparse
import json
from urllib.parse import quote
from uuid import uuid4

import httpx
from sqlalchemy import text

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.storage.factory import create_private_object_storage


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect Phase 18 knowledge readiness.")
    parser.add_argument(
        "--probe-storage",
        action="store_true",
        help="Create, read, public-access-check, and delete one synthetic private object.",
    )
    args = parser.parse_args()
    settings = get_settings()
    result = {
        "database_ready": False,
        "pgvector_ready": False,
        "json_fallback_ready": False,
        "storage_enabled": settings.knowledge_storage_enabled,
        "document_ingest_enabled": settings.document_ingest_enabled,
        "embeddings_enabled": settings.knowledge_embeddings_enabled,
        "shadow_retrieval_enabled": settings.knowledge_shadow_retrieval_enabled,
        "pgvector_primary_enabled": settings.knowledge_pgvector_primary_enabled,
        "storage_probe": "not_requested",
    }
    with SessionLocal() as db:
        try:
            db.execute(text("select 1"))
            result["database_ready"] = True
            if db.bind is not None and db.bind.dialect.name == "postgresql":
                result["pgvector_ready"] = bool(
                    db.execute(text("SELECT 1 FROM pg_extension WHERE extname = 'vector'")).scalar()
                )
        except Exception:
            result["database_ready"] = False

    from app.rag.vector_store import JsonVectorStore

    result["json_fallback_ready"] = JsonVectorStore().path.exists()
    if args.probe_storage:
        result["storage_probe"] = _probe_private_storage()

    print(json.dumps(result, sort_keys=True))
    required = result["database_ready"] and result["json_fallback_ready"]
    if args.probe_storage:
        required = required and result["storage_probe"] == "passed"
    return 0 if required else 1


def _probe_private_storage() -> str:
    settings = get_settings()
    if not settings.knowledge_storage_enabled:
        return "storage_disabled"
    storage = create_private_object_storage()
    marker = uuid4().hex
    key = (
        f"knowledge/private/phase18probe/sources/ksrc_probe_{marker}/"
        f"documents/kdoc_probe_{marker}/versions/kver_probe_{marker}/original"
    )
    content = b"phase18-private-storage-probe"
    outcome = "probe_failed"
    cleanup_failed = False
    try:
        storage.put_create_only(key=key, content=content, content_type="text/plain")
        if storage.get_bounded(key=key, max_bytes=len(content)).content != content:
            outcome = "read_mismatch"
        else:
            # A publicly readable bucket would return this synthetic object without
            # credentials. Anything other than 200 preserves the public boundary.
            encoded_key = "/".join(quote(part, safe="") for part in key.split("/"))
            public_url = f"{settings.supabase_url.rstrip('/')}/storage/v1/object/public/{settings.supabase_storage_bucket}/{encoded_key}"
            response = httpx.get(public_url, timeout=settings.supabase_storage_timeout_seconds)
            outcome = "public_access_detected" if response.status_code == 200 else "passed"
    finally:
        try:
            storage.delete(key=key)
        except Exception:
            cleanup_failed = True
    return "cleanup_failed" if cleanup_failed else outcome


if __name__ == "__main__":
    raise SystemExit(main())
