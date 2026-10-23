from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class LLMRequest:
    prompt: str
    timeout_seconds: float
    max_output_tokens: int | None = None
    system_prompt: str = ""


@dataclass(frozen=True)
class SynthesisBudget:
    total_tokens: int
    max_output_tokens: int
    cost_ceiling_microusd: int
    deadline_monotonic: float | None = None


@dataclass(frozen=True)
class LLMResponse:
    text: str
    provider: str
    model: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    cost_microusd: int | None = None
    # Field names only: malformed or contract-missing usage. Raw provider
    # values are deliberately not retained in provenance.
    usage_invalid_fields: tuple[str, ...] = ()


class LLMProvider(Protocol):
    name: str
    model: str

    def generate(self, request: LLMRequest) -> LLMResponse:
        raise NotImplementedError
