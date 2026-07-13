from app.options.payoff import (
    breakeven_price,
    build_scenarios,
    default_scenario_prices,
    max_loss,
    max_profit,
)
from app.options.schemas import OptionsAnalysisRequest, OptionsAnalysisResponse
from app.options.volatility import bid_ask_spread, days_to_expiration, volatility_summary

OPTIONS_DISCLAIMER = (
    "Options analysis is educational and scenario-based. It is not financial advice, "
    "not a recommendation to buy or sell, and not a guarantee of payoff or liquidity."
)


def analyze_option(request: OptionsAnalysisRequest) -> OptionsAnalysisResponse:
    scenario_prices = request.scenario_prices or default_scenario_prices(
        request.underlying_price,
        request.strike_price,
    )
    spread, spread_pct = bid_ask_spread(request.bid, request.ask)
    expiry_days = days_to_expiration(request.expiration_date)
    missing_data = []
    if request.implied_volatility is None:
        missing_data.append("implied_volatility")
    if request.bid is None or request.ask is None:
        missing_data.append("bid/ask")
    if request.expiration_date is None:
        missing_data.append("expiration_date")

    risks = [
        "Premium paid can be lost if the option expires out of the money.",
        "Bid/ask spread can materially affect entry and exit marks.",
        "Implied volatility can fall even if spot direction is favorable.",
        "Scenario payoff ignores venue fees, funding, collateral constraints, and execution slippage.",
    ]
    if expiry_days is not None and expiry_days < 0:
        risks.append("Expiration date is in the past relative to the local system date.")
    elif expiry_days is not None and expiry_days <= 7:
        risks.append("Short time to expiration increases sensitivity to timing and decay assumptions.")

    return OptionsAnalysisResponse(
        option_type=request.option_type,
        underlying_asset=request.underlying_asset,
        breakeven_price=breakeven_price(
            request.option_type,
            request.strike_price,
            request.premium,
        ),
        max_loss=max_loss(request.premium, request.contracts),
        max_profit=max_profit(request.option_type, request.strike_price, request.premium, request.contracts),
        bid_ask_spread=spread,
        bid_ask_spread_pct=spread_pct,
        days_to_expiration=expiry_days,
        scenarios=build_scenarios(
            request.option_type,
            request.strike_price,
            request.premium,
            request.contracts,
            scenario_prices,
        ),
        assumptions=[
            "Payoffs model a long option position using premium paid as maximum loss.",
            "Scenario table is deterministic and does not assign probabilities.",
            "Outputs exclude fees, margin, funding, settlement, and execution constraints.",
        ],
        risks=risks,
        missing_data=missing_data,
        volatility_summary=volatility_summary(request.implied_volatility, request.volatility_thesis),
        disclaimer=OPTIONS_DISCLAIMER,
    )
