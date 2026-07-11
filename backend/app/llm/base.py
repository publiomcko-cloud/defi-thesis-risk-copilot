from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class LLMRequest:
    prompt: str
    timeout_seconds: float


@dataclass(frozen=True)
class LLMResponse:
    text: str
    provider: str
    model: str


class LLMProvider(Protocol):
    name: str
    model: str

    def generate(self, request: LLMRequest) -> LLMResponse:
        raise NotImplementedError
