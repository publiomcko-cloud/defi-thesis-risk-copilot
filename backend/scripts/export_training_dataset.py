import argparse
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.db.session import SessionLocal
from app.ml.dataset_export import DEFAULT_TRAINING_DATASET_PATH, export_training_examples


def main() -> int:
    parser = argparse.ArgumentParser(description="Export candidate risk training examples.")
    parser.add_argument("--output", type=Path, default=DEFAULT_TRAINING_DATASET_PATH)
    args = parser.parse_args()

    with SessionLocal() as db:
        examples = export_training_examples(db, args.output)

    print(f"Exported {len(examples)} training examples to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
