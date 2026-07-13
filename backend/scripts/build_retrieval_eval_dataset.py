import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.rag.evaluation import DEFAULT_EVAL_DATASET_PATH, write_default_eval_dataset


def main() -> int:
    cases = write_default_eval_dataset(DEFAULT_EVAL_DATASET_PATH)
    print(f"Wrote {len(cases)} retrieval eval cases to {DEFAULT_EVAL_DATASET_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
