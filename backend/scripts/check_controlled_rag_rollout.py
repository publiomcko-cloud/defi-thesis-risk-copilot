"""Print redacted Phase 19I durable-RAG rollout readiness evidence.

The command is read-only. A ``primary-synthetic`` check is deliberately
blocked unless an explicitly isolated, non-production environment opts in.
It never changes feature flags or prints credentials, bucket names, object
keys, tenant identifiers, report data, or retrieval content.
"""

from __future__ import annotations

import argparse
import json

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.operations.controlled_rag import controlled_rag_readiness


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mode",
        choices=("shadow", "primary-synthetic"),
        default="shadow",
        help="Check production-safe shadow mode or isolated primary synthetic mode.",
    )
    args = parser.parse_args()
    mode = "primary_synthetic" if args.mode == "primary-synthetic" else "shadow"
    settings = get_settings()
    with SessionLocal() as db:
        readiness = controlled_rag_readiness(db, settings, mode=mode)
    print(json.dumps(readiness.payload(), sort_keys=True))
    return 0 if readiness.status == "ready" else 2


if __name__ == "__main__":
    raise SystemExit(main())
