"""Run the Phase 18G durable-public versus JSON fallback retrieval gate.

The command bootstraps only the checked-in curated corpus into the current
database transaction with in-memory private objects and rolls it back.  It
never contacts Supabase Storage, mutates production data, or imports tenant
content.  Use it in CI or before enabling the primary feature flag.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.db.session import SessionLocal
from app.knowledge.public_corpus import import_curated_public_corpus
from app.knowledge.retrieval_evaluation import compare_public_retrievers
from app.rag.evaluation import DEFAULT_EVAL_DATASET_PATH
from app.rag.ingest import ingest_knowledge_base
from app.storage.memory import InMemoryPrivateObjectStorage


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare public JSON and durable retrieval quality.")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_EVAL_DATASET_PATH)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--top-k", type=int, default=1)
    args = parser.parse_args()
    output_path = args.output or Path(tempfile.gettempdir()) / "phase18g_public_retrieval_eval.json"
    json_output = output_path.with_name(output_path.stem + ".json-fallback.json")

    # The checked-in Markdown is the JSON fallback source of truth. Rebuild its
    # ignored local index so CI never depends on a developer-generated file.
    ingest_knowledge_base()
    with SessionLocal() as db:
        try:
            import_curated_public_corpus(db, InMemoryPrivateObjectStorage())
            comparison = compare_public_retrievers(
                db,
                dataset_path=args.dataset,
                json_output_path=json_output,
                top_k=args.top_k,
            )
        finally:
            # This is evaluation evidence only. Do not persist bootstrap rows.
            db.rollback()
    output_path.write_text(json.dumps(comparison, indent=2), encoding="utf-8")
    durable = comparison["durable_public"]
    print(
        f"durable public retrieval: {durable['passed_cases']}/{durable['total_cases']} "
        f"({durable['pass_rate']:.0%}); precision@{args.top_k}={durable['precision_at_k']:.0%}; "
        f"recall={durable['recall']:.0%}; citation issues={durable['citation_issue_count']}; "
        f"cutover_gate_passed={comparison['cutover_gate_passed']}"
    )
    return 0 if comparison["cutover_gate_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
