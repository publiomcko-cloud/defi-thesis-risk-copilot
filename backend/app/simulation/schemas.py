from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class SimulationRequest(BaseModel):
    strategy_description: str | None = None
    protocols: list[str] = Field(default_factory=list)
    implied_apy: float | None = Field(default=None, ge=0)
    supply_apy: float | None = Field(default=None, ge=0)
    incentive_apy: float | None = Field(default=None, ge=0)
    borrow_apy: float | None = Field(default=None, ge=0)
    ltv: float | None = Field(default=None, ge=0, le=1)
    lltv: float | None = Field(default=None, ge=0, le=1)
    collateral_value_usd: float | None = Field(default=None, ge=0)
    debt_value_usd: float | None = Field(default=None, ge=0)
    liquidity_usd: float | None = Field(default=None, ge=0)
    pt_price: float | None = Field(default=None, ge=0)
    maturity_date: str | None = None
    borrow_apy_shock_multiplier: float = Field(default=2.0, ge=1)
    liquidity_shock_pct: float = Field(default=0.5, ge=0, le=1)
    collateral_drawdown_pct: float = Field(default=0.1, ge=0, le=1)
    early_exit_discount_pct: float = Field(default=0.03, ge=0, le=1)
    slippage_bps: float | None = Field(default=None, ge=0)

    model_config = ConfigDict(extra="allow")


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
