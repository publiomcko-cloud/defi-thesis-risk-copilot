from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.percentages import normalize_percent_style


OptionType = Literal["call", "put"]


class OptionsAnalysisRequest(BaseModel):
    option_type: OptionType
    underlying_asset: str = Field(default="ETH", min_length=1, max_length=32)
    underlying_price: float = Field(ge=0, le=1_000_000_000)
    strike_price: float = Field(ge=0, le=1_000_000_000)
    premium: float = Field(ge=0, le=1_000_000_000)
    expiration_date: str | None = Field(default=None, max_length=32)
    implied_volatility: float | None = Field(default=None, ge=0, le=20)
    bid: float | None = Field(default=None, ge=0, le=1_000_000_000)
    ask: float | None = Field(default=None, ge=0, le=1_000_000_000)
    contracts: float = Field(default=1, gt=0, le=1_000_000)
    scenario_prices: list[float] = Field(default_factory=list, max_length=100)
    volatility_thesis: str | None = Field(default=None, max_length=2000)

    model_config = ConfigDict(extra="forbid")

    @field_validator("implied_volatility", mode="before")
    @classmethod
    def normalize_implied_volatility(cls, value: object) -> object:
        return normalize_percent_style(value)


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
