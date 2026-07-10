from typing import Any

from app.risk.framework import RiskComponent, RiskScore, map_score_to_rating

VOLATILE_ASSETS = {"eth", "weth", "wsteth", "btc", "wbtc", "sol"}


def score_strategy_risk(
    strategy_description: str,
    protocols: list[str],
    manual_inputs: dict[str, Any],
    missing_data: list[str],
) -> RiskScore:
    lowered = strategy_description.lower()
    score = 1
    components = [
        RiskComponent(
            category="protocol_risk",
            points=1,
            reason="Base DeFi protocol and smart-contract risk.",
        )
    ]

    known_protocols = [protocol for protocol in protocols if protocol != "unknown"]
    if len(known_protocols) > 1:
        components.append(
            RiskComponent(
                "composability_risk",
                1,
                "Strategy combines multiple protocols.",
            )
        )
        score += 1

    if _uses_leverage(lowered, manual_inputs):
        components.append(
            RiskComponent(
                "liquidation_risk",
                1,
                "Strategy uses borrowing, leverage, or a positive LTV.",
            )
        )
        score += 1

    if _has_volatile_collateral(manual_inputs):
        components.append(
            RiskComponent(
                "market_risk",
                1,
                "Collateral appears to be a volatile asset.",
            )
        )
        score += 1

    if "borrow" in lowered or manual_inputs.get("borrow_apy") is not None:
        components.append(
            RiskComponent(
                "borrow_rate_risk",
                1,
                "Borrow APY can change and compress strategy spread.",
            )
        )
        score += 1

    liquidity = manual_inputs.get("liquidity_usd")
    if liquidity is None or float(liquidity or 0) < 500_000:
        components.append(
            RiskComponent(
                "liquidity_risk",
                1,
                "Liquidity is low or unknown.",
            )
        )
        score += 1

    if "exit" in lowered or "secondary market" in lowered or "pt" in lowered:
        components.append(
            RiskComponent(
                "maturity_risk",
                1,
                "Exit may depend on PT maturity or secondary-market liquidity.",
            )
        )
        score += 1

    if _missing_contains(missing_data, "oracle") or "oracle" in lowered:
        components.append(
            RiskComponent(
                "oracle_risk",
                1,
                "Oracle configuration is unclear or explicitly relevant.",
            )
        )
        score += 1

    if "incentive" in lowered or "reward" in lowered or "emission" in lowered:
        components.append(
            RiskComponent(
                "incentive_risk",
                1,
                "Yield may depend on temporary rewards or incentives.",
            )
        )
        score += 1

    if missing_data:
        components.append(
            RiskComponent(
                "operational_risk",
                1,
                "Missing data lowers confidence and increases execution risk.",
            )
        )
        score += 1

    rating = map_score_to_rating(score)
    return RiskScore(
        score=score,
        rating=rating,
        components=components,
        confidence=_confidence_from_missing_data(missing_data),
        main_risk_drivers=[
            component.category for component in components if component.points > 0
        ][:5],
    )


def _uses_leverage(description: str, manual_inputs: dict[str, Any]) -> bool:
    return (
        "leverage" in description
        or "borrow" in description
        or float(manual_inputs.get("ltv") or 0) > 0
    )


def _has_volatile_collateral(manual_inputs: dict[str, Any]) -> bool:
    collateral = str(manual_inputs.get("collateral_asset") or "").lower()
    return collateral in VOLATILE_ASSETS


def _missing_contains(missing_data: list[str], needle: str) -> bool:
    return any(needle in item.lower() for item in missing_data)


def _confidence_from_missing_data(missing_data: list[str]) -> str:
    if not missing_data:
        return "high"
    if len(missing_data) <= 3:
        return "medium"
    return "low"
