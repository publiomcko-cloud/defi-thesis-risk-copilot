from dataclasses import dataclass
from typing import Literal

RiskRating = Literal["Conservative", "Moderate", "Aggressive", "Very Risky"]

RISK_CATEGORIES = [
    "protocol_risk",
    "market_risk",
    "liquidity_risk",
    "oracle_risk",
    "liquidation_risk",
    "borrow_rate_risk",
    "maturity_risk",
    "composability_risk",
    "operational_risk",
    "incentive_risk",
]


@dataclass(frozen=True)
class RiskComponent:
    category: str
    points: int
    reason: str


@dataclass(frozen=True)
class RiskScore:
    score: int
    rating: RiskRating
    components: list[RiskComponent]
    confidence: str
    main_risk_drivers: list[str]


def map_score_to_rating(score: int) -> RiskRating:
    if score <= 2:
        return "Conservative"
    if score <= 4:
        return "Moderate"
    if score <= 6:
        return "Aggressive"
    return "Very Risky"
