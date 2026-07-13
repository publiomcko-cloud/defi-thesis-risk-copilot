from typing import Literal

from pydantic import BaseModel, Field


OptionType = Literal["call", "put"]


class OptionsAnalysisRequest(BaseModel):
    option_type: OptionType
    underlying_asset: str = "ETH"
    underlying_price: float = Field(ge=0)
    strike_price: float = Field(ge=0)
    premium: float = Field(ge=0)
    expiration_date: str | None = None
    implied_volatility: float | None = Field(default=None, ge=0)
    bid: float | None = Field(default=None, ge=0)
    ask: float | None = Field(default=None, ge=0)
    contracts: float = Field(default=1, gt=0)
    scenario_prices: list[float] = Field(default_factory=list)
    volatility_thesis: str | None = None


class OptionScenario(BaseModel):
    underlying_price: float
    intrinsic_value: float
    payoff: float
    return_on_premium_pct: float | None
    moneyness: str


class OptionsAnalysisResponse(BaseModel):
    option_type: OptionType
    underlying_asset: str
    breakeven_price: float
    max_loss: float
    max_profit: str
    bid_ask_spread: float | None
    bid_ask_spread_pct: float | None
    days_to_expiration: int | None
    scenarios: list[OptionScenario]
    assumptions: list[str]
    risks: list[str]
    missing_data: list[str]
    volatility_summary: str
    disclaimer: str
