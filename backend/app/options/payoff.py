from app.options.schemas import OptionScenario, OptionType


def breakeven_price(option_type: OptionType, strike_price: float, premium: float) -> float:
    if option_type == "call":
        return strike_price + premium
    return max(strike_price - premium, 0)


def intrinsic_value(option_type: OptionType, underlying_price: float, strike_price: float) -> float:
    if option_type == "call":
        return max(underlying_price - strike_price, 0)
    return max(strike_price - underlying_price, 0)


def payoff(option_type: OptionType, underlying_price: float, strike_price: float, premium: float, contracts: float) -> float:
    return (intrinsic_value(option_type, underlying_price, strike_price) - premium) * contracts


def max_loss(premium: float, contracts: float) -> float:
    return premium * contracts


def max_profit(option_type: OptionType, strike_price: float, premium: float, contracts: float) -> str:
    if option_type == "call":
        return "Uncapped before fees because call payoff increases as the underlying rises."
    profit = max((strike_price - premium) * contracts, 0)
    return f"{profit:.6g} if the underlying settles at zero before fees."


def build_scenarios(
    option_type: OptionType,
    strike_price: float,
    premium: float,
    contracts: float,
    scenario_prices: list[float],
) -> list[OptionScenario]:
    return [
        OptionScenario(
            underlying_price=price,
            intrinsic_value=intrinsic_value(option_type, price, strike_price) * contracts,
            payoff=payoff(option_type, price, strike_price, premium, contracts),
            return_on_premium_pct=_return_on_premium(
                payoff(option_type, price, strike_price, premium, contracts),
                premium * contracts,
            ),
            moneyness=_moneyness(option_type, price, strike_price),
        )
        for price in scenario_prices
    ]


def default_scenario_prices(underlying_price: float, strike_price: float) -> list[float]:
    prices = {
        round(underlying_price * 0.75, 6),
        round(underlying_price * 0.9, 6),
        round(underlying_price, 6),
        round(strike_price, 6),
        round(underlying_price * 1.1, 6),
        round(underlying_price * 1.25, 6),
    }
    return sorted(price for price in prices if price >= 0)


def _return_on_premium(value: float, premium_paid: float) -> float | None:
    if premium_paid == 0:
        return None
    return value / premium_paid


def _moneyness(option_type: OptionType, underlying_price: float, strike_price: float) -> str:
    if underlying_price == strike_price:
        return "at_the_money"
    if option_type == "call":
        return "in_the_money" if underlying_price > strike_price else "out_of_the_money"
    return "in_the_money" if underlying_price < strike_price else "out_of_the_money"
