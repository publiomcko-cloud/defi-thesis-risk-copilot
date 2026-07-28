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
    expected_empty_cases: int
    correct_empty_cases: int
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
    positive_cases = [item for item in results if not item["expect_empty"]]
    source_coverage = (
        sum(bool(item["retrieved_chunk_ids"]) for item in positive_cases) / len(positive_cases)
        if positive_cases
        else 1.0
    )
    precision_at_k = sum(item["precision_at_k"] for item in results) / len(results) if results else 0.0
    recall = sum(item["recall"] for item in results) / len(results) if results else 0.0
    expected_empty_cases = sum(item["expect_empty"] for item in results)
    correct_empty_cases = sum(
        item["expect_empty"] and not item["retrieved_chunk_ids"] for item in results
    )
    return DurablePublicRetrievalSummary(
        retriever="durable_public_pgvector",
        total_cases=len(results),
        passed_cases=passed,
        pass_rate=passed / len(results) if results else 0.0,
        citation_issue_count=citation_issues,
        source_coverage=source_coverage,
        precision_at_k=precision_at_k,
        recall=recall,
        expected_empty_cases=expected_empty_cases,
        correct_empty_cases=correct_empty_cases,
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
            and durable_summary.correct_empty_cases == durable_summary.expected_empty_cases
        ),
    }


def _evaluate_case(db: Session, case: RetrievalEvalCase, top_k: int) -> dict:
    protocol_filter = None
    if case.metadata_filters and case.metadata_filters.get("protocol"):
        protocol_filter = [case.metadata_filters["protocol"]]
    retrieved = retrieve_public_durable_context(db, case.query, protocols=protocol_filter, top_k=top_k)
    top = retrieved[0] if retrieved else None
    matched_terms = [
        term
        for term in case.expected_terms
        if term.lower() in "\n".join(item.text.lower() for item in retrieved)
    ]
    citation_issues = validate_retrieval_citations(retrieved)
    retrieved_chunk_ids = [item.chunk_id for item in retrieved]
    retrieved_source_ids = [
        str(item.metadata.get("citation_lineage", {}).get("source_id", ""))
        for item in retrieved
    ]
    expected_references = {
        *(f"source:{identifier}" for identifier in case.relevant_source_ids),
        *(f"chunk:{identifier}" for identifier in case.relevant_chunk_ids),
    }
    # Older, caller-supplied datasets are accepted for compatibility, but the
    # checked-in Phase 18 dataset always declares immutable source/chunk IDs.
    # This is an evaluation fallback only; it never becomes a retrieval filter.
    if not expected_references and case.expected_protocol and not case.expect_empty:
        expected_references.add(f"protocol:{case.expected_protocol}")
    retrieved_references = {
        *(f"source:{identifier}" for identifier in retrieved_source_ids if identifier),
        *(f"chunk:{identifier}" for identifier in retrieved_chunk_ids),
        *(f"protocol:{item.metadata.get('protocol', '')}" for item in retrieved),
    }
    relevant_retrieved = [
        item
        for item in retrieved
        if (
            f"source:{item.metadata.get('citation_lineage', {}).get('source_id', '')}"
            in expected_references
            or f"chunk:{item.chunk_id}" in expected_references
            or f"protocol:{item.metadata.get('protocol', '')}" in expected_references
        )
    ]
    reference_hits = expected_references & retrieved_references
    if case.expect_empty:
        precision_at_k = 1.0 if not retrieved else 0.0
        recall = 1.0
        passed = not retrieved and not citation_issues
    else:
        precision_at_k = len(relevant_retrieved) / len(retrieved) if retrieved else 0.0
        recall = len(reference_hits) / len(expected_references) if expected_references else 0.0
        passed = bool(retrieved and reference_hits and recall == 1.0 and not citation_issues)
    return {
        "id": case.id,
        "passed": passed,
        "expect_empty": case.expect_empty,
        "top_chunk_id": top.chunk_id if top else None,
        "top_protocol": top.metadata.get("protocol") if top else None,
        "retrieved_chunk_ids": retrieved_chunk_ids,
        "retrieved_source_ids": retrieved_source_ids,
        "relevant_source_ids": case.relevant_source_ids,
        "relevant_chunk_ids": case.relevant_chunk_ids,
        "matched_reference_ids": sorted(reference_hits),
        "precision_at_k": precision_at_k,
        "recall": recall,
        "matched_expected_terms": matched_terms,
        "citation_issues": citation_issues,
    }
