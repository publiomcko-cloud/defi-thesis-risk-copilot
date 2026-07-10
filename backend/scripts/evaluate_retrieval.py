import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.rag.retriever import Retriever


QUESTIONS = [
    "What is a Pendle PT?",
    "What is maturity risk?",
    "What is LLTV?",
    "What is Health Factor?",
    "What is oracle risk?",
    "What is liquidation risk?",
]


def main() -> int:
    retriever = Retriever()
    for question in QUESTIONS:
        print(f"\nQuestion: {question}")
        results = retriever.retrieve(question, top_k=2)
        if not results:
            print("  No results")
            continue
        for result in results:
            metadata = result.metadata
            print(
                "  "
                f"{metadata['protocol']} / {metadata['section_title']} "
                f"score={result.similarity_score:.3f}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
