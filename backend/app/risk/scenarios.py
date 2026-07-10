from app.risk.framework import RiskScore


def generate_stress_scenarios(risk_score: RiskScore) -> list[str]:
    scenarios = [
        "Collateral price drops 10%, reducing borrowing buffer.",
        "Borrow APY doubles and compresses or eliminates net spread.",
        "Liquidity drops 50%, increasing slippage and exit uncertainty.",
        "User exits before maturity and receives worse pricing than expected.",
        "Oracle data becomes unavailable or stale during market volatility.",
        "Incentives disappear and headline yield falls.",
    ]
    if risk_score.rating in {"Aggressive", "Very Risky"}:
        scenarios.append("Multiple adverse events happen together across protocols.")
    return scenarios
