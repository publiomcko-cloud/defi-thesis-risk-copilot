from typing import Any

import httpx

from app.core.config import Settings
from app.llm.base import LLMProvider, LLMRequest, LLMResponse


class OllamaProvider:
    name = "ollama"

    def __init__(self, base_url: str, model: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model

    def generate(self, request: LLMRequest) -> LLMResponse:
        response = httpx.post(
            f"{self.base_url}/api/generate",
            json={
                "model": self.model,
                "prompt": request.prompt,
                "stream": False,
                "format": "json",
            },
            timeout=request.timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
        return LLMResponse(
            text=str(payload.get("response") or ""),
            provider=self.name,
            model=self.model,
        )


class OpenAICompatibleProvider:
    name = "openai_compatible"

    def __init__(self, base_url: str, api_key: str, model: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model

    def generate(self, request: LLMRequest) -> LLMResponse:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "You write educational, non-advisory DeFi risk reports.",
                },
                {"role": "user", "content": request.prompt},
            ],
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
        }
        response = httpx.post(
            f"{self.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json=payload,
            timeout=request.timeout_seconds,
        )
        response.raise_for_status()
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        return LLMResponse(
            text=str(content or ""),
            provider=self.name,
            model=self.model,
        )


def get_llm_provider(settings: Settings) -> LLMProvider | None:
    provider = settings.llm_provider.lower()
    if provider in {"disabled", "none", ""}:
        return None
    if provider == "ollama":
        return OllamaProvider(settings.ollama_base_url, settings.ollama_model)
    if provider == "openai_compatible":
        if not settings.openai_compatible_base_url or not settings.openai_compatible_api_key:
            return None
        return OpenAICompatibleProvider(
            settings.openai_compatible_base_url,
            settings.openai_compatible_api_key,
            settings.openai_compatible_model,
        )
    return None
