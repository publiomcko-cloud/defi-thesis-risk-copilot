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
        payload = _ollama_generate_payload(self.base_url, self.model, request)
        return _ollama_response_from_payload(payload, self.model)


def _ollama_generate_payload(
    base_url: str,
    model: str,
    request: LLMRequest,
    *,
    response_format: str | dict[str, Any] = "json",
) -> dict[str, Any]:
    """Use the genuine Ollama HTTP API with the same bounded request contract."""

    response = httpx.post(
        f"{base_url}/api/generate",
        json={
            "model": model,
            "prompt": request.prompt,
            "system": request.system_prompt,
            "stream": False,
            "format": response_format,
            **(
                {"options": {"num_predict": request.max_output_tokens}}
                if request.max_output_tokens is not None
                else {}
            ),
        },
        timeout=request.timeout_seconds,
    )
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise ValueError("Ollama response must be a JSON object")
    return payload


def _ollama_response_from_payload(payload: dict[str, Any], model: str) -> LLMResponse:
    """Parse shared Ollama token accounting without persisting raw usage."""

    input_tokens, input_invalid = _required_usage(payload, "prompt_eval_count")
    output_tokens, output_invalid = _required_usage(payload, "eval_count")
    derived_total = _bounded_usage(input_tokens, output_tokens)
    invalid_fields = [
        field
        for field, invalid in (
            ("prompt_eval_count", input_invalid),
            ("eval_count", output_invalid),
        )
        if invalid
    ]
    if not input_invalid and not output_invalid and derived_total is None:
        invalid_fields.append("total_tokens")
    return LLMResponse(
        text=str(payload.get("response") or ""),
        provider="ollama",
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        # Ollama reports input and output counts but no separate total.
        # Let synthesis derive the effective total without claiming the
        # provider reported one.
        total_tokens=None,
        usage_invalid_fields=tuple(invalid_fields),
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
                    "content": request.system_prompt or "You write educational, non-advisory DeFi risk reports.",
                },
                {"role": "user", "content": request.prompt},
            ],
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
        }
        if request.max_output_tokens is not None:
            payload["max_tokens"] = request.max_output_tokens
        response = httpx.post(
            f"{self.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json=payload,
            timeout=request.timeout_seconds,
        )
        response.raise_for_status()
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        raw_usage = data.get("usage")
        if isinstance(raw_usage, dict):
            usage = raw_usage
            usage_invalid_fields: list[str] = []
            input_tokens, input_invalid = _required_usage(usage, "prompt_tokens")
            output_tokens, output_invalid = _required_usage(usage, "completion_tokens")
            total_tokens, total_invalid = _required_usage(usage, "total_tokens")
            usage_invalid_fields.extend(
                field
                for field, invalid in (
                    ("prompt_tokens", input_invalid),
                    ("completion_tokens", output_invalid),
                    ("total_tokens", total_invalid),
                )
                if invalid
            )
        else:
            input_tokens = output_tokens = total_tokens = None
            usage_invalid_fields = ["usage"]
        return LLMResponse(
            text=str(content or ""),
            provider=self.name,
            model=self.model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            usage_invalid_fields=tuple(usage_invalid_fields),
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


def _bounded_usage(value: object, additional: object | None = None) -> int | None:
    if additional is not None:
        if not isinstance(value, int) or isinstance(value, bool) or not isinstance(additional, int) or isinstance(additional, bool):
            return None
        value += additional
    if not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= 10_000_000:
        return None
    return value


def _required_usage(payload: dict[str, Any], field: str) -> tuple[int | None, bool]:
    """Read one contract-required token count without erasing invalidity."""

    if field not in payload:
        return None, True
    value = payload[field]
    if not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= 10_000_000:
        return None, True
    return value, False
