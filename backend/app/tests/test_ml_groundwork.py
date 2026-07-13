import json
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.ml.dataset_export import export_training_examples, label_schema
from app.ml.risk_classifier import BaselineRiskClassifier, preserve_deterministic_rating
from app.models.analysis_request import AnalysisRequestModel
from app.models.report import ReportModel


def test_training_dataset_export_includes_label_schema(tmp_path: Path) -> None:
    db = _build_test_session()
    _seed_report(db)
    output_path = tmp_path / "risk_training_examples.json"

    examples = export_training_examples(db, output_path)

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert len(examples) == 1
    assert payload[0]["labels"]["risk_rating"] == "Aggressive"
    assert payload[0]["labels"]["deterministic_risk_score"] == 6
    assert payload[0]["labels"]["label_source"] == "deterministic_rules"
    assert payload[0]["labels"]["human_ground_truth"] is False
    assert payload[0]["labels"]["protocol_category"] == "multi_protocol"
    assert payload[0]["labels"]["missing_data_severity"] == "low"
    assert payload[0]["source_references"][0]["protocol"] == "pendle"
    assert payload[0]["normalized_features"]["has_sources"] is True
    assert payload[0]["metadata"]["label_source"] == "deterministic_rules"
    assert "risk_rating" in label_schema()
    assert "deterministic_risk_score" in label_schema()


def test_baseline_classifier_is_advisory_only() -> None:
    prediction = BaselineRiskClassifier().predict(
        strategy_description="Leveraged Pendle PT strategy borrowing on Morpho with oracle risk.",
        protocols=["pendle", "morpho"],
        missing_data=["oracle configuration", "liquidity depth", "exit route"],
        manual_inputs={"ltv": 0.7},
    )

    assert prediction.advisory_only is True
    assert prediction.status == "shadow_evaluation_only"
    assert prediction.predicted_rating in {"Aggressive", "Very Risky"}
    assert "Deterministic rule-based risk scoring remains authoritative" in prediction.explanation


def test_classifier_output_cannot_override_deterministic_rating() -> None:
    prediction = BaselineRiskClassifier().predict(
        strategy_description="Borrowed position with low liquidity and maturity risk.",
        protocols=["pendle", "morpho"],
        missing_data=["liquidity depth", "oracle configuration", "exit route"],
        manual_inputs={"ltv": 0.8, "liquidity_usd": 10_000},
    )

    merged = preserve_deterministic_rating("Moderate", prediction)

    assert merged["risk_rating"] == "Moderate"
    assert merged["classifier_advisory"]["predicted_rating"] != merged["risk_rating"]
    assert merged["authoritative_source"] == "deterministic_rule_based_scoring"
    assert merged["shadow_mode_only"] is True


def test_model_training_artifacts_are_not_required_for_classifier() -> None:
    prediction = BaselineRiskClassifier().predict(
        strategy_description="Simple Aave supply strategy.",
        protocols=["aave"],
        missing_data=[],
    )

    assert prediction.status == "shadow_evaluation_only"
    assert prediction.advisory_only is True
    assert "No model-training artifact is loaded" in prediction.limitations[0]


def _build_test_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    return Session()


def _seed_report(db) -> None:
    request = AnalysisRequestModel(
        id="analysis_training_test",
        strategy_description="Leveraged Pendle PT strategy using Morpho borrow.",
        protocols=["pendle", "morpho"],
        market_url=None,
        manual_inputs_json={"ltv": 0.65},
        analysis_depth="standard",
    )
    report = ReportModel(
        id="report_training_test",
        analysis_request_id=request.id,
        title="Strategy Risk Report",
        risk_rating="Aggressive",
        summary="Leveraged fixed-yield strategy with liquidation and liquidity risk.",
        report_markdown="# Report",
        report_json={
            "report_id": "report_training_test",
            "status": "completed",
            "risk_rating": "Aggressive",
            "executive_summary": "Leveraged fixed-yield strategy with liquidation and liquidity risk.",
            "strategy_description": "Leveraged Pendle PT strategy using Morpho borrow.",
            "protocols": ["pendle", "morpho"],
            "assumptions": [],
            "missing_data": ["oracle configuration"],
            "sections": [
                {
                    "title": "Risk Analysis",
                    "content": "Rule-based score: 6. Liquidation, oracle, borrow rate, and liquidity risks are relevant.",
                }
            ],
            "sources": [
                {
                    "title": "Pendle Notes - Principal Tokens (pendle)",
                    "source_type": "knowledge_base",
                    "url": "/knowledge_base/pendle/README.md",
                    "protocol": "pendle",
                }
            ],
            "disclaimer": "Educational only.",
        },
    )
    db.add(request)
    db.add(report)
    db.commit()
