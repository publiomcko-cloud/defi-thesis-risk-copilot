from pathlib import Path

from app.models.discovered_item import DiscoveredItemModel
from app.models.evaluation_result import EvaluationResultModel
from app.models.review_item import ReviewItemModel


HUMAN_APPROVAL_STATEMENT = (
    "This source was automatically discovered and human-approved before ingestion."
)

NON_ADVISORY_DISCLAIMER = (
    "This knowledge-base entry is for research and educational purposes only. "
    "It is not financial advice, not a recommendation to buy or sell, and not "
    "an instruction to execute any transaction."
)


def build_discovered_markdown(
    discovered_item: DiscoveredItemModel,
    review_item: ReviewItemModel,
    evaluation_result: EvaluationResultModel,
) -> str:
    notes = discovered_item.raw_payload.get("source_quality_notes", [])
    assumptions = evaluation_result.report_json.get("assumptions", [])
    return "\n".join(
        [
            f"# {discovered_item.title}",
            "",
            "## Source Metadata",
            f"- Protocol: {discovered_item.protocol or 'unknown'}",
            f"- Chain: {discovered_item.chain or 'unknown'}",
            f"- Source URL: {discovered_item.url or 'not provided'}",
            f"- Source type: {discovered_item.source_type}",
            f"- Discovery source: {discovered_item.source}",
            f"- Discovery timestamp: {discovered_item.discovered_at.isoformat()}",
            f"- Evaluation timestamp: {evaluation_result.created_at.isoformat()}",
            "",
            "## Review Metadata",
            f"- Review item ID: {review_item.id}",
            f"- Review status: {review_item.status}",
            f"- Reviewer notes: {review_item.reviewer_notes or 'No reviewer notes provided.'}",
            f"- Human approval statement: {HUMAN_APPROVAL_STATEMENT}",
            "",
            "## Evaluation Summary",
            evaluation_result.risk_summary,
            "",
            "## Risk Rating",
            f"- Rating: {evaluation_result.risk_rating}",
            f"- Score: {evaluation_result.risk_score}",
            f"- Confidence: {evaluation_result.confidence}",
            "",
            "## Missing Data",
            _list_or_none(evaluation_result.missing_data_json),
            "",
            "## Assumptions",
            _list_or_none(assumptions),
            "",
            "## Source Quality Notes",
            _list_or_none(notes),
            "",
            "## Disclaimer",
            NON_ADVISORY_DISCLAIMER,
            "",
        ]
    )


def write_discovered_markdown(
    root: Path,
    discovered_item: DiscoveredItemModel,
    review_item: ReviewItemModel,
    evaluation_result: EvaluationResultModel,
) -> Path:
    protocol = _safe_path_part(discovered_item.protocol or "unknown")
    target_dir = root / "discovered" / protocol
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / f"{_safe_path_part(review_item.id)}.md"
    target_path.write_text(
        build_discovered_markdown(discovered_item, review_item, evaluation_result),
        encoding="utf-8",
    )
    return target_path


def _list_or_none(items) -> str:
    if not items:
        return "- None recorded."
    return "\n".join(f"- {item}" for item in items)


def _safe_path_part(value: str) -> str:
    return "".join(char if char.isalnum() or char in {"-", "_"} else "_" for char in value.lower())
