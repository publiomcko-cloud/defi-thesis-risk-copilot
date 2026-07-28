import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from app.rag.citations import validate_retrieval_citations
from app.rag.hybrid_retriever import HybridRetriever
from app.rag.retriever import RetrievalResult, Retriever
from app.rag.vector_store import JsonVectorStore


DEFAULT_EVAL_DATASET_PATH = Path(__file__).resolve().parents[2] / "retrieval_eval_dataset.json"
DEFAULT_EVAL_RESULTS_PATH = Path(__file__).resolve().parents[2] / "retrieval_eval_results.json"


@dataclass(frozen=True)
class RetrievalEvalCase:
    id: str
    query: str
    expected_protocol: str | None
    expected_terms: list[str]
    metadata_filters: dict[str, str] | None = None
    relevant_source_ids: list[str] = field(default_factory=list)
    relevant_chunk_ids: list[str] = field(default_factory=list)
    expect_empty: bool = False


@dataclass(frozen=True)
class RetrievalEvalCaseResult:
    id: str
    query: str
    passed: bool
    top_chunk_id: str | None
    top_protocol: str | None
    matched_expected_terms: list[str]
    citation_issues: list[str]
    expect_empty: bool = False


@dataclass(frozen=True)
class RetrievalEvalSummary:
    retriever: str
    total_cases: int
    passed_cases: int
    pass_rate: float
    citation_issue_count: int
    cases: list[RetrievalEvalCaseResult]


def default_eval_cases() -> list[RetrievalEvalCase]:
    return [
        RetrievalEvalCase(
            "pendle_pt", "What is a Pendle PT?", "pendle", ["principal token", "pt"],
            relevant_source_ids=["ksrc_pub_a1da37ff088089e679ef"],
            relevant_chunk_ids=["kchunk_pub_f2bd825dac767963c577"],
        ),
        RetrievalEvalCase(
            "pendle_maturity", "What is maturity risk?", "pendle", ["maturity"],
            relevant_source_ids=["ksrc_pub_a1da37ff088089e679ef"],
            relevant_chunk_ids=["kchunk_pub_b0061bed5ca98cb8509e"],
        ),
        RetrievalEvalCase(
            "morpho_lltv", "What is LLTV in Morpho?", "morpho", ["lltv"],
            relevant_source_ids=["ksrc_pub_b731019df5bc97b0e572"],
            relevant_chunk_ids=["kchunk_pub_edeceb532eed80d5d5aa"],
        ),
        RetrievalEvalCase(
            "aave_health_factor", "What is Health Factor?", "aave", ["health factor"],
            relevant_source_ids=["ksrc_pub_b024f4b882c2dfe9a317"],
            relevant_chunk_ids=["kchunk_pub_8bad75b61af4c0ef3657"],
        ),
        RetrievalEvalCase(
            "oracle_risk", "What is oracle risk?", "chainlink", ["oracle"],
            relevant_source_ids=["ksrc_pub_6f512f98508809c459d5"],
            relevant_chunk_ids=["kchunk_pub_11029256a78a363519fd"],
        ),
        RetrievalEvalCase(
            "liquidation_risk", "What is liquidation risk?", "internal_notes", ["liquidation"],
            relevant_source_ids=["ksrc_pub_7101b1f4894761eee339"],
            relevant_chunk_ids=["kchunk_pub_5b5ff2d0e9e664ec1a02"],
        ),
        RetrievalEvalCase(
            "irrelevant_no_answer", "quantum satellite manufacturing", None, [], expect_empty=True,
        ),
    ]


def write_default_eval_dataset(path: Path = DEFAULT_EVAL_DATASET_PATH) -> list[RetrievalEvalCase]:
    cases = default_eval_cases()
    path.write_text(
        json.dumps([asdict(case) for case in cases], indent=2),
        encoding="utf-8",
    )
    return cases


def load_eval_dataset(path: Path = DEFAULT_EVAL_DATASET_PATH) -> list[RetrievalEvalCase]:
    if not path.exists():
        return write_default_eval_dataset(path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [
        RetrievalEvalCase(
            id=item["id"],
            query=item["query"],
            expected_protocol=item.get("expected_protocol"),
            expected_terms=item.get("expected_terms", []),
            metadata_filters=item.get("metadata_filters"),
            relevant_source_ids=item.get("relevant_source_ids", []),
            relevant_chunk_ids=item.get("relevant_chunk_ids", []),
            expect_empty=bool(item.get("expect_empty", False)),
        )
        for item in payload
    ]


def evaluate_retriever(
    retriever_name: str = "hybrid",
    dataset_path: Path = DEFAULT_EVAL_DATASET_PATH,
    output_path: Path = DEFAULT_EVAL_RESULTS_PATH,
    top_k: int = 3,
    store: JsonVectorStore | None = None,
) -> RetrievalEvalSummary:
    cases = load_eval_dataset(dataset_path)
    retriever = _build_retriever(retriever_name, store)
    results = [
        _evaluate_case(case, retriever, top_k=top_k)
        for case in cases
    ]
    passed = sum(1 for result in results if result.passed)
    citation_issue_count = sum(len(result.citation_issues) for result in results)
    summary = RetrievalEvalSummary(
        retriever=retriever_name,
        total_cases=len(results),
        passed_cases=passed,
        pass_rate=passed / len(results) if results else 0.0,
        citation_issue_count=citation_issue_count,
        cases=results,
    )
    output_path.write_text(json.dumps(_summary_to_dict(summary), indent=2), encoding="utf-8")
    return summary


def _build_retriever(
    retriever_name: str,
    store: JsonVectorStore | None = None,
) -> Retriever | HybridRetriever:
    if retriever_name == "local":
        return Retriever(store)
    if retriever_name == "hybrid":
        return HybridRetriever(store)
    if retriever_name == "hybrid_semantic":
        return HybridRetriever(store, semantic_enabled=True)
    raise ValueError("retriever_name must be local, hybrid, or hybrid_semantic")


def _evaluate_case(
    case: RetrievalEvalCase,
    retriever: Retriever | HybridRetriever,
    top_k: int,
) -> RetrievalEvalCaseResult:
    if isinstance(retriever, HybridRetriever):
        retrieved = retriever.retrieve(
            case.query,
            top_k=top_k,
            metadata_filters=case.metadata_filters,
        )
    else:
        retrieved = retriever.retrieve(case.query, top_k=top_k)

    top = retrieved[0] if retrieved else None
    matched_terms = _matched_terms(case.expected_terms, retrieved)
    citation_issues = validate_retrieval_citations(retrieved)
    passed = (
        not retrieved and not citation_issues
        if case.expect_empty
        else bool(
            top
            and top.metadata.get("protocol") == case.expected_protocol
            and matched_terms
            and not citation_issues
        )
    )
    return RetrievalEvalCaseResult(
        id=case.id,
        query=case.query,
        passed=passed,
        top_chunk_id=top.chunk_id if top else None,
        top_protocol=top.metadata.get("protocol") if top else None,
        matched_expected_terms=matched_terms,
        citation_issues=citation_issues,
        expect_empty=case.expect_empty,
    )


def _matched_terms(expected_terms: list[str], results: list[RetrievalResult]) -> list[str]:
    combined_text = "\n".join(result.text.lower() for result in results)
    return [term for term in expected_terms if term.lower() in combined_text]


def _summary_to_dict(summary: RetrievalEvalSummary) -> dict:
    return {
        "retriever": summary.retriever,
        "total_cases": summary.total_cases,
        "passed_cases": summary.passed_cases,
        "pass_rate": summary.pass_rate,
        "citation_issue_count": summary.citation_issue_count,
        "cases": [asdict(case) for case in summary.cases],
    }
