from typing import Any

import httpx

from app.core.config import get_settings


class DefiLlamaClient:
    def __init__(self, base_url: str | None = None, timeout: float = 8.0) -> None:
        self.base_url = (base_url or get_settings().defillama_base_url).rstrip("/")
        self.timeout = timeout

    def protocols(self) -> list[dict[str, Any]]:
        payload = self._get_json("/protocols")
        return payload if isinstance(payload, list) else []

    def yield_pools(self) -> list[dict[str, Any]]:
        payload = self._get_json("https://yields.llama.fi/pools")
        data = payload.get("data", []) if isinstance(payload, dict) else []
        return data if isinstance(data, list) else []

    def options_overview(self) -> list[dict[str, Any]]:
        return self._list_from_optional_endpoint("/overview/options")

    def open_interest_overview(self) -> list[dict[str, Any]]:
        return self._list_from_optional_endpoint("/overview/open-interest")

    def fees_overview(self) -> list[dict[str, Any]]:
        return self._list_from_optional_endpoint("/overview/fees")

    def _list_from_optional_endpoint(self, path: str) -> list[dict[str, Any]]:
        try:
            payload = self._get_json(path)
        except httpx.HTTPError:
            return []
        if isinstance(payload, list):
            return payload
        if isinstance(payload, dict):
            for key in ("protocols", "data", "results"):
                value = payload.get(key)
                if isinstance(value, list):
                    return value
        return []

    def _get_json(self, path_or_url: str) -> Any:
        url = path_or_url if path_or_url.startswith("http") else f"{self.base_url}{path_or_url}"
        with httpx.Client(timeout=self.timeout) as client:
            response = client.get(url)
            response.raise_for_status()
            return response.json()
