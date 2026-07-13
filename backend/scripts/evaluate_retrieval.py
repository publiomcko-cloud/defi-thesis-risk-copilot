import argparse
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.rag.evaluation import (
    DEFAULT_EVAL_DATASET_PATH,
    DEFAULT_EVAL_RESULTS_PATH,
    evaluate_retriever,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate RAG retrieval quality.")
    parser.add_argument(
        "--retriever",
        choices=("local", "hybrid", "hybrid_semantic"),
        default="hybrid",
    )
    parser.add_argument("--dataset", type=Path, default=DEFAULT_EVAL_DATASET_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_EVAL_RESULTS_PATH)
    parser.add_argument("--top-k", type=int, default=3)
    args = parser.parse_args()

    summary = evaluate_retriever(
        retriever_name=args.retriever,
        dataset_path=args.dataset,
        output_path=args.output,
        top_k=args.top_k,
    )
    print(
        f"Retrieval eval passed {summary.passed_cases}/{summary.total_cases} "
        f"({summary.pass_rate:.0%}); citation issues={summary.citation_issue_count}. "
        f"Results written to {args.output}"
    )
    return 0 if summary.pass_rate >= 0.8 and summary.citation_issue_count == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
