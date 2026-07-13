from dataclasses import asdict, dataclass
from typing import Any, Literal

from app.risk.framework import RiskRating, map_score_to_rating


ClassifierStatus = Literal["advisory_only"]


@dataclass(frozen=True)
class BaselineRiskPrediction:
    predicted_rating: RiskRating
    confidence: str
    advisory_only: bool
    status: ClassifierStatus
    features: dict[str, Any]
    explanation: str


class BaselineRiskClassifier:
    """Simple advisory baseline for future ML comparison.

    The prediction is intentionally separate from deterministic scoring and must
    not be used as the source of truth for report risk ratings.
    """

    def predict(
        self,
        strategy_description: str,
        protocols: list[str],
        missing_data: list[str],
        manual_inputs: dict[str, Any] | None = None,
    ) -> BaselineRiskPrediction:
        manual_inputs = manual_inputs or {}
        lowered = strategy_description.lower()
        score = 1
        features: dict[str, Any] = {
            "protocol_count": len([protocol for protocol in protocols if protocol != "unknown"]),
            "missing_data_count": len(missing_data),
            "uses_leverage": _uses_leverage(lowered, manual_inputs),
            "mentions_oracle": "oracle" in lowered or any("oracle" in item.lower() for item in missing_data),
            "mentions_maturity": "maturity" in lowered or "pt" in lowered,
            "has_low_or_unknown_liquidity": _has_low_or_unknown_liquidity(manual_inputs),
        }

        if features["protocol_count"] > 1:
            score += 1
        if features["uses_leverage"]:
            score += 2
        if features["mentions_oracle"]:
            score += 1
        if features["mentions_maturity"]:
            score += 1
        if features["has_low_or_unknown_liquidity"]:
            score += 1
        if features["missing_data_count"] >= 3:
            score += 1

        return BaselineRiskPrediction(
            predicted_rating=map_score_to_rating(score),
            confidence=_confidence(features["missing_data_count"]),
            advisory_only=True,
            status="advisory_only",
            features=features,
            explanation=(
                "Baseline classifier prediction is advisory and for evaluation only. "
                "Deterministic rule-based risk scoring remains authoritative."
            ),
        )


def preserve_deterministic_rating(
    deterministic_rating: RiskRating,
    prediction: BaselineRiskPrediction,
) -> dict[str, Any]:
    return {
        "risk_rating": deterministic_rating,
        "classifier_advisory": asdict(prediction),
        "authoritative_source": "deterministic_rule_based_scoring",
    }


def _uses_leverage(description: str, manual_inputs: dict[str, Any]) -> bool:
    return (
        "leverage" in description
        or "borrow" in description
        or float(manual_inputs.get("ltv") or 0) > 0
    )


def _has_low_or_unknown_liquidity(manual_inputs: dict[str, Any]) -> bool:
    liquidity = manual_inputs.get("liquidity_usd")
    return liquidity is None or float(liquidity or 0) < 500_000


def _confidence(missing_data_count: int) -> str:
    if missing_data_count == 0:
        return "medium"
    if missing_data_count <= 3:
        return "low"
    return "very_low"
