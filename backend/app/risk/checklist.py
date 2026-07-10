from app.risk.framework import RiskScore


def generate_monitoring_checklist(risk_score: RiskScore) -> list[str]:
    items = [
        "Track borrow APY and utilization.",
        "Track liquidity depth and estimated slippage.",
        "Track collateral price movement and LTV.",
        "Track oracle status and data freshness.",
        "Track protocol parameter or governance changes.",
        "Review missing data before increasing position size.",
    ]
    if "maturity_risk" in risk_score.main_risk_drivers:
        items.append("Track PT maturity date and secondary-market exit conditions.")
    if "incentive_risk" in risk_score.main_risk_drivers:
        items.append("Track reward emissions and incentive end dates.")
    return items
