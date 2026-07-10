from app.agents.strategy_parser import ParsedStrategy
from app.risk.framework import RiskScore
from app.risk.scoring import score_strategy_risk


def score_parsed_strategy(
    parsed_strategy: ParsedStrategy,
    missing_data: list[str],
) -> RiskScore:
    return score_strategy_risk(
        strategy_description=parsed_strategy.description,
        protocols=parsed_strategy.protocols,
        manual_inputs=parsed_strategy.manual_inputs,
        missing_data=missing_data,
    )
