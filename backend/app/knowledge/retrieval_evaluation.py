"""Repeatable Phase 18G comparison metrics for the public retrieval cutover."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

from sqlalchemy.orm import Session

from app.knowledge.public_retriever import retrieve_public_durable_context
from app.rag.citations import validate_retrieval_citations
from app.rag.evaluation import RetrievalEvalCase, RetrievalEvalSummary, evaluate_retriever, load_eval_dataset


@dataclass(frozen=True)
class DurablePublicRetrievalSummary:
    retriever: str
    total_cases: int
    passed_cases: int
    pass_rate: float
    citation_issue_count: int
    source_coverage: float
    precision_at_k: float
    recall: float
    cases: list[dict]


def evaluate_durable_public_retrieval(
    db: Session,
    *,
    dataset_path: Path,
    top_k: int = 3,
) -> DurablePublicRetrievalSummary:
    """Evaluate only durable approved-public content with no tenant bypass."""

    cases = load_eval_dataset(dataset_path)
    results = [_evaluate_case(db, case, top_k) for case in cases]
    passed = sum(item["passed"] for item in results)
    citation_issues = sum(len(item["citation_issues"]) for item in results)
    source_coverage = sum(bool(item["top_chunk_id"]) for item in results) / len(results) if results else 0.0
    retrieved_cases = sum(bool(item["top_chunk_id"]) for item in results)
    precision_at_k = passed / retrieved_cases if retrieved_cases else 0.0
    recall = passed / len(results) if results else 0.0
    return DurablePublicRetrievalSummary(
        retriever="durable_public_pgvector",
        total_cases=len(results),
        passed_cases=passed,
        pass_rate=passed / len(results) if results else 0.0,
        citation_issue_count=citation_issues,
        source_coverage=source_coverage,
        precision_at_k=precision_at_k,
        recall=recall,
        cases=results,
    )


def compare_public_retrievers(
    db: Session,
    *,
    dataset_path: Path,
    json_output_path: Path,
    top_k: int = 3,
) -> dict:
    """Return comparable JSON-fallback and durable-public quality evidence."""

    json_summary: RetrievalEvalSummary = evaluate_retriever(
        retriever_name="hybrid",
        dataset_path=dataset_path,
        output_path=json_output_path,
        top_k=top_k,
    )
    durable_summary = evaluate_durable_public_retrieval(
        db,
        dataset_path=dataset_path,
        top_k=top_k,
    )
    return {
        "json_fallback": {
            "pass_rate": json_summary.pass_rate,
            "citation_issue_count": json_summary.citation_issue_count,
            "passed_cases": json_summary.passed_cases,
            "total_cases": json_summary.total_cases,
        },
        "durable_public": asdict(durable_summary),
        "cutover_gate_passed": (
            durable_summary.pass_rate >= 0.8
            and durable_summary.precision_at_k >= 0.8
            and durable_summary.recall >= 0.8
            and durable_summary.citation_issue_count == 0
            and durable_summary.source_coverage == 1.0
        ),
    }


def _evaluate_case(db: Session, case: RetrievalEvalCase, top_k: int) -> dict:
    retrieved = retrieve_public_durable_context(
        db,
        case.query,
        protocols=[case.expected_protocol],
        top_k=top_k,
    )
    top = retrieved[0] if retrieved else None
    matched_terms = [
        term
        for term in case.expected_terms
        if term.lower() in "\n".join(item.text.lower() for item in retrieved)
    ]
    citation_issues = validate_retrieval_citations(retrieved)
    return {
        "id": case.id,
        "passed": bool(
            top
            and top.metadata.get("protocol") == case.expected_protocol
            and matched_terms
            and not citation_issues
        ),
        "top_chunk_id": top.chunk_id if top else None,
        "top_protocol": top.metadata.get("protocol") if top else None,
        "matched_expected_terms": matched_terms,
        "citation_issues": citation_issues,
    }
