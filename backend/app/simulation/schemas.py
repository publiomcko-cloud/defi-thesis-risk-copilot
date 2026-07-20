from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.percentages import normalize_percent_style


class SimulationRequest(BaseModel):
    strategy_description: str | None = Field(default=None, max_length=5000)
    protocols: list[str] = Field(default_factory=list, max_length=10)
    implied_apy: float | None = Field(default=None, ge=0, le=10)
    supply_apy: float | None = Field(default=None, ge=0, le=10)
    incentive_apy: float | None = Field(default=None, ge=0, le=10)
    borrow_apy: float | None = Field(default=None, ge=0, le=10)
    ltv: float | None = Field(default=None, ge=0, le=1)
    lltv: float | None = Field(default=None, ge=0, le=1)
    collateral_value_usd: float | None = Field(default=None, ge=0, le=1_000_000_000_000)
    debt_value_usd: float | None = Field(default=None, ge=0, le=1_000_000_000_000)
    liquidity_usd: float | None = Field(default=None, ge=0, le=1_000_000_000_000)
    pt_price: float | None = Field(default=None, ge=0, le=1_000_000_000)
    maturity_date: str | None = Field(default=None, max_length=32)
    borrow_apy_shock_multiplier: float = Field(default=2.0, ge=1, le=20)
    liquidity_shock_pct: float = Field(default=0.5, ge=0, le=1)
    collateral_drawdown_pct: float = Field(default=0.1, ge=0, le=1)
    early_exit_discount_pct: float = Field(default=0.03, ge=0, le=1)
    slippage_bps: float | None = Field(default=None, ge=0, le=100_000)

    model_config = ConfigDict(extra="forbid")

    @field_validator(
        "implied_apy",
        "supply_apy",
        "incentive_apy",
        "borrow_apy",
        "ltv",
        "lltv",
        "liquidity_shock_pct",
        "collateral_drawdown_pct",
        "early_exit_discount_pct",
        mode="before",
    )
    @classmethod
    def normalize_percentage_fields(cls, value: object) -> object:
        return normalize_percent_style(value)


class SimulationScenario(BaseModel):
    name: str
    scenario_type: Literal[
        "net_spread",
        "borrow_apy_shock",
        "liquidity_slippage_shock",
        "collateral_drawdown",
        "early_exit",
        "incentive_removal",
        "combined_adverse",
    ]
    result: dict
    formula: str
    assumptions: list[str]
    missing_data: list[str]
    interpretation: str


class SimulationResponse(BaseModel):
    status: Literal["completed", "partial"]
    scenarios: list[SimulationScenario]
    assumptions: list[str]
    missing_data: list[str]
    disclaimer: str
