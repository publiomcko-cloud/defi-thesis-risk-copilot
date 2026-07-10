from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


AnalysisDepth = Literal["quick", "standard", "deep"]
RiskRating = Literal["Conservative", "Moderate", "Aggressive", "Very Risky"]
AnalysisStatus = Literal["completed"]


class ManualInputs(BaseModel):
    borrow_apy: float | None = Field(default=None, ge=0)
    implied_apy: float | None = Field(default=None, ge=0)
    liquidity_usd: float | None = Field(default=None, ge=0)
    ltv: float | None = Field(default=None, ge=0, le=1)
    lltv: float | None = Field(default=None, ge=0, le=1)

    model_config = ConfigDict(extra="allow")


class AnalysisRequest(BaseModel):
    strategy_description: str = Field(min_length=10)
    protocols: list[str] = Field(default_factory=list)
    market_url: str | None = None
    manual_inputs: ManualInputs = Field(default_factory=ManualInputs)
    analysis_depth: AnalysisDepth = "standard"


class AnalysisResponse(BaseModel):
    report_id: str
    status: AnalysisStatus
    risk_rating: RiskRating
    summary: str
