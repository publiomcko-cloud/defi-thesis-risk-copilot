from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


AnalysisDepth = Literal["quick", "standard", "deep"]
RiskRating = Literal["Conservative", "Moderate", "Aggressive", "Very Risky"]
AnalysisStatus = Literal["completed"]


class ManualInputs(BaseModel):
    borrow_apy: float | None = Field(default=None, ge=0, le=10)
    implied_apy: float | None = Field(default=None, ge=0, le=10)
    liquidity_usd: float | None = Field(default=None, ge=0, le=1_000_000_000_000)
    ltv: float | None = Field(default=None, ge=0, le=1)
    lltv: float | None = Field(default=None, ge=0, le=1)
    collateral_asset: str | None = Field(default=None, max_length=64)
    debt_asset: str | None = Field(default=None, max_length=64)
    pt_price: float | None = Field(default=None, ge=0, le=1_000_000_000)
    maturity_date: str | None = Field(default=None, max_length=32)
    token_id: str | None = Field(default=None, max_length=128)
    supply_apy: float | None = Field(default=None, ge=0, le=10)
    liquidation_threshold: float | None = Field(default=None, ge=0, le=1)
    reserve_asset: str | None = Field(default=None, max_length=64)

    model_config = ConfigDict(extra="forbid")


class AnalysisRequest(BaseModel):
    strategy_description: str = Field(min_length=10, max_length=5000)
    protocols: list[str] = Field(default_factory=list, max_length=10)
    market_url: str | None = Field(default=None, max_length=2048)
    manual_inputs: ManualInputs = Field(default_factory=ManualInputs)
    analysis_depth: AnalysisDepth = "standard"

    model_config = ConfigDict(extra="forbid")


class AnalysisResponse(BaseModel):
    report_id: str
    status: AnalysisStatus
    risk_rating: RiskRating
    summary: str
