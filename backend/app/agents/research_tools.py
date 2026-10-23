"""Typed, server-owned tool contracts for the bounded synchronous workflow."""

from __future__ import annotations

import json
from enum import StrEnum
from hashlib import sha256
from typing import Callable, TypeVar

from pydantic import BaseModel, ConfigDict, Field

from app.risk.framework import RiskRating


class ResearchToolName(StrEnum):
    PROTOCOL_RETRIEVAL = "protocol_retrieval"
    MARKET_OBSERVATION = "market_observation"
    DETERMINISTIC_RISK = "deterministic_risk"
    REPORT_SYNTHESIS = "report_synthesis"


class ToolInput(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ProtocolRetrievalInput(ToolInput):
    query: str = Field(min_length=1, max_length=5_000)
    protocols: list[str] = Field(max_length=3)
    top_k: int = Field(ge=1, le=8)


class ProtocolRetrievalOutput(BaseModel):
    chunk_ids: list[str] = Field(max_length=8)
    protocols: list[str] = Field(max_length=3)
    count: int = Field(ge=0, le=8)

    model_config = ConfigDict(extra="forbid")


class MarketObservationInput(ToolInput):
    protocols: list[str] = Field(max_length=3)
    manual_inputs: dict = Field(max_length=30)


class MarketObservationOutput(BaseModel):
    status: str = Field(max_length=32)
    sources: list[str] = Field(max_length=8)
    missing_fields: list[str] = Field(max_length=64)

    model_config = ConfigDict(extra="forbid")


class DeterministicRiskInput(ToolInput):
    strategy_description: str = Field(min_length=1, max_length=10_000)
    protocols: list[str] = Field(max_length=3)
    missing_data: list[str] = Field(max_length=128)


class DeterministicRiskOutput(BaseModel):
    score: int = Field(ge=0, le=10)
    rating: RiskRating
    confidence: str = Field(max_length=32)

    model_config = ConfigDict(extra="forbid")


class ReportSynthesisInput(ToolInput):
    report_id: str = Field(min_length=1, max_length=64)
    research_question: str | None = Field(default=None, max_length=2_000)
    source_document_count: int = Field(ge=0, le=8)
    token_budget: int = Field(ge=512, le=12_000)
    cost_ceiling_microusd: int = Field(ge=0)


class ReportSynthesisOutput(BaseModel):
    used_llm: bool
    outcome: str = Field(max_length=64)
    provider: str | None = Field(default=None, max_length=64)
    model_key: str | None = Field(default=None, max_length=128)
    total_tokens: int | None = Field(default=None, ge=0, le=10_000_000)
    cost_microusd: int | None = Field(default=None, ge=0)

    model_config = ConfigDict(extra="forbid")


ToolInputType = TypeVar("ToolInputType", bound=ToolInput)
ToolOutputType = TypeVar("ToolOutputType", bound=BaseModel)

TOOL_CONTRACTS: dict[ResearchToolName, tuple[type[ToolInput], type[BaseModel]]] = {
    ResearchToolName.PROTOCOL_RETRIEVAL: (ProtocolRetrievalInput, ProtocolRetrievalOutput),
    ResearchToolName.MARKET_OBSERVATION: (MarketObservationInput, MarketObservationOutput),
    ResearchToolName.DETERMINISTIC_RISK: (DeterministicRiskInput, DeterministicRiskOutput),
    ResearchToolName.REPORT_SYNTHESIS: (ReportSynthesisInput, ReportSynthesisOutput),
}
ALLOWED_RESEARCH_TOOLS = frozenset(TOOL_CONTRACTS)


class ToolBudgetExceeded(RuntimeError):
    pass


class ResearchToolLedger:
    """Validates each server-selected tool call and records digest-only lineage."""

    def __init__(
        self,
        max_invocations: int,
        max_model_calls: int = 2,
        execution_guard: Callable[[], None] | None = None,
    ) -> None:
        if not 1 <= max_invocations <= 8:
            raise ValueError("research tool invocation limit must be between 1 and 8")
        if not 1 <= max_model_calls <= 2:
            raise ValueError("research model-call limit must be between one and two")
        self.max_invocations = max_invocations
        self.max_model_calls = max_model_calls
        self.execution_guard = execution_guard
        self.model_calls = 0
        self.trace: list[dict] = []

    def invoke(
        self,
        tool: ResearchToolName,
        payload: dict,
        handler: Callable[[ToolInput], ToolOutputType],
        *,
        pass_number: int,
        fallback: bool = False,
    ) -> ToolOutputType:
        if tool not in ALLOWED_RESEARCH_TOOLS:
            raise ValueError("research tool is not allowlisted")
        if len(self.trace) >= self.max_invocations:
            raise ToolBudgetExceeded("research tool invocation limit reached")
        if tool == ResearchToolName.REPORT_SYNTHESIS and self.model_calls >= self.max_model_calls:
            raise ToolBudgetExceeded("research model-call limit reached")
        if pass_number not in {1, 2}:
            raise ValueError("research pass number is outside the bounded workflow")

        input_type, output_type = TOOL_CONTRACTS[tool]
        parsed_input = input_type.model_validate(payload)
        if self.execution_guard is not None:
            self.execution_guard()
        if tool == ResearchToolName.REPORT_SYNTHESIS:
            self.model_calls += 1
        result = handler(parsed_input)
        if self.execution_guard is not None:
            self.execution_guard()
        if not isinstance(result, output_type):
            raise TypeError(f"{tool.value} returned an invalid typed output")
        self.trace.append(
            {
                "tool": tool.value,
                "pass_number": pass_number,
                "input_sha256": _digest(parsed_input.model_dump(mode="json")),
                "output_sha256": _digest(result.model_dump(mode="json")),
                "status": "fallback" if fallback else "completed",
            }
        )
        return result

    @property
    def remaining_invocations(self) -> int:
        return self.max_invocations - len(self.trace)


def _digest(payload: dict) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    return sha256(encoded).hexdigest()
