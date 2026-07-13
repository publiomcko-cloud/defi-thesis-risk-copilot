import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.report import ReportModel


DEFAULT_TRAINING_DATASET_PATH = (
    Path(__file__).resolve().parents[3]
    / "model-training"
    / "datasets"
    / "risk_training_examples.json"
)


@dataclass(frozen=True)
class RiskTrainingLabels:
    risk_rating: str
    deterministic_risk_score: int | None
    main_risk_drivers: list[str]
    protocol_category: str
    missing_data_severity: str
    strategy_type: str
    label_source: str = "deterministic_rules"
    human_ground_truth: bool = False


@dataclass(frozen=True)
class RiskTrainingExample:
    id: str
    report_id: str
    strategy_description: str
    protocols: list[str]
    sections: list[dict[str, str]]
    missing_data: list[str]
    source_references: list[dict[str, str | None]]
    normalized_features: dict[str, Any]
    labels: RiskTrainingLabels
    source: str = "persisted_report"
    metadata: dict[str, Any] | None = None


def export_training_examples(
    db: Session,
    output_path: Path = DEFAULT_TRAINING_DATASET_PATH,
) -> list[RiskTrainingExample]:
    examples = build_training_examples(db)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps([_example_to_dict(example) for example in examples], indent=2),
        encoding="utf-8",
    )
    return examples


def build_training_examples(db: Session) -> list[RiskTrainingExample]:
    records = db.scalars(select(ReportModel).order_by(ReportModel.created_at)).all()
    return [_record_to_training_example(record) for record in records]


def label_schema() -> dict[str, str]:
    return {
        "risk_rating": "Deterministic report risk rating.",
        "deterministic_risk_score": "Rule-based risk score when present in report text.",
        "main_risk_drivers": "Risk categories inferred from report sections and missing data.",
        "protocol_category": "Single protocol, multi-protocol, or unknown protocol grouping.",
        "missing_data_severity": "none, low, medium, or high based on missing_data length.",
        "strategy_type": "Heuristic strategy family such as lending, leverage, fixed_yield, options, or generic_defi.",
        "label_source": "Always deterministic_rules for current exports.",
        "human_ground_truth": "False until examples are reviewed and labeled by humans.",
    }


def _record_to_training_example(record: ReportModel) -> RiskTrainingExample:
    report = record.report_json
    strategy_description = str(report.get("strategy_description", ""))
    protocols = list(report.get("protocols") or [])
    missing_data = list(report.get("missing_data") or [])
    sections = [
        {"title": str(section.get("title", "")), "content": str(section.get("content", ""))}
        for section in report.get("sections", [])
        if isinstance(section, dict)
    ]
    combined_text = " ".join(
        [strategy_description]
        + [section["title"] for section in sections]
        + [section["content"] for section in sections]
        + missing_data
    )
    labels = RiskTrainingLabels(
        risk_rating=str(report.get("risk_rating", record.risk_rating)),
        deterministic_risk_score=_extract_deterministic_risk_score(combined_text),
        main_risk_drivers=_infer_main_risk_drivers(combined_text),
        protocol_category=_protocol_category(protocols),
        missing_data_severity=_missing_data_severity(missing_data),
        strategy_type=_strategy_type(strategy_description, protocols),
    )
    sources = [
        {
            "title": str(source.get("title", "")),
            "source_type": str(source.get("source_type", "")),
            "url": source.get("url"),
            "protocol": source.get("protocol"),
        }
        for source in report.get("sources", [])
        if isinstance(source, dict)
    ]
    return RiskTrainingExample(
        id=f"training_{record.id}",
        report_id=record.id,
        strategy_description=strategy_description,
        protocols=protocols,
        sections=sections,
        missing_data=missing_data,
        source_references=sources,
        normalized_features={
            "protocol_count": len([protocol for protocol in protocols if protocol != "unknown"]),
            "missing_data_count": len(missing_data),
            "section_count": len(sections),
            "has_sources": bool(sources),
            "strategy_type": labels.strategy_type,
            "protocol_category": labels.protocol_category,
        },
        labels=labels,
        metadata={
            "label_source": "deterministic_rules",
            "human_ground_truth": False,
            "production_authoritative": False,
            "notes": (
                "Candidate example for experimentation. Labels come from deterministic "
                "report rules or rule-derived heuristics, not human-reviewed ground truth."
            ),
        },
    )


def _extract_deterministic_risk_score(text: str) -> int | None:
    match = re.search(r"Rule-based score:\s*(\d+)", text, flags=re.IGNORECASE)
    if match:
        return int(match.group(1))
    match = re.search(r"score\s+(\d+)", text, flags=re.IGNORECASE)
    return int(match.group(1)) if match else None


def _infer_main_risk_drivers(text: str) -> list[str]:
    lowered = text.lower()
    drivers = []
    keyword_map = {
        "liquidation_risk": ("liquidation", "ltv", "lltv", "health factor"),
        "oracle_risk": ("oracle", "price feed"),
        "liquidity_risk": ("liquidity", "slippage", "exit"),
        "borrow_rate_risk": ("borrow", "variable rate", "apy shock"),
        "maturity_risk": ("maturity", "expiry", "principal token", "pt"),
        "composability_risk": ("composability", "multiple protocols"),
        "incentive_risk": ("incentive", "reward", "emission"),
        "operational_risk": ("missing data", "manual input", "unclear"),
    }
    for driver, keywords in keyword_map.items():
        if any(keyword in lowered for keyword in keywords):
            drivers.append(driver)
    return drivers[:5] or ["protocol_risk"]


def _protocol_category(protocols: list[str]) -> str:
    known = [protocol for protocol in protocols if protocol and protocol != "unknown"]
    if not known:
        return "unknown"
    if len(known) == 1:
        return f"single_protocol:{known[0]}"
    return "multi_protocol"


def _missing_data_severity(missing_data: list[str]) -> str:
    if not missing_data:
        return "none"
    if len(missing_data) <= 2:
        return "low"
    if len(missing_data) <= 5:
        return "medium"
    return "high"


def _strategy_type(description: str, protocols: list[str]) -> str:
    lowered = " ".join([description.lower(), " ".join(protocols).lower()])
    if "option" in lowered or "volatility" in lowered:
        return "options"
    if "borrow" in lowered or "leverage" in lowered or "ltv" in lowered:
        return "leveraged_lending"
    if "pt" in lowered or "fixed yield" in lowered or "pendle" in lowered:
        return "fixed_yield"
    if "lend" in lowered or "supply" in lowered or "aave" in lowered or "morpho" in lowered:
        return "lending"
    return "generic_defi"


def _example_to_dict(example: RiskTrainingExample) -> dict[str, Any]:
    return asdict(example)
