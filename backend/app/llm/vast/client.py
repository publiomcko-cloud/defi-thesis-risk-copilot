from typing import Any

import httpx

from app.core.config import Settings
from app.llm.vast.schemas import VastOffer


class VastClientError(RuntimeError):
    pass


class VastClient:
    def __init__(self, settings: Settings, api_key: str | None = None) -> None:
        self.settings = settings
        self.api_key = api_key or settings.vast_api_key
        self.base_url = settings.vast_api_base_url.rstrip("/")
        self.dry_run = settings.vast_dry_run

    def search_offers(self) -> list[VastOffer]:
        if self.dry_run:
            return [
                VastOffer(
                    id="dry_offer_1",
                    gpu_name=_first_allowed_gpu(self.settings),
                    hourly_cost_usd=min(0.25, self.settings.vast_max_hourly_cost_usd),
                    gpu_ram_gb=max(float(self.settings.vast_min_gpu_ram_gb), 24.0),
                    disk_gb=float(self.settings.vast_disk_gb),
                    verified=True,
                    rentable=True,
                    public_endpoint_url="http://dry-run-vast.local:8000",
                    metadata={"dry_run": True},
                )
            ]
        payload = self._request("GET", "/bundles/")
        offers = payload.get("offers") or payload.get("results") or payload
        if not isinstance(offers, list):
            raise VastClientError("Unexpected Vast.ai offer response shape")
        return [_offer_from_payload(item) for item in offers if isinstance(item, dict)]

    def rent_instance(
        self,
        offer: VastOffer,
        image: str,
        model: str,
        disk_gb: int,
        *,
        request_id: str,
    ) -> dict[str, Any]:
        if self.dry_run:
            return {
                "instance_id": f"dry_instance_{offer.id}",
                "contract_id": f"dry_contract_{offer.id}",
                "public_endpoint_url": offer.public_endpoint_url or "http://dry-run-vast.local:8000",
                "dry_run": True,
                "provider_request_id": request_id,
            }
        payload = {
            "client_id": "me",
            "image": image,
            "disk": disk_gb,
            "env": {"MODEL": model},
            # Vast.ai support for a caller request identifier must be verified before
            # real rentals are enabled. It is still persisted locally for reconciliation.
            "client_request_id": request_id,
        }
        data = self._request("PUT", f"/asks/{offer.id}/", json=payload)
        return {
            "instance_id": str(data.get("instance_id") or data.get("new_contract") or data.get("id") or ""),
            "contract_id": str(data.get("contract_id") or data.get("new_contract") or ""),
            "public_endpoint_url": data.get("public_endpoint_url") or data.get("url"),
            "raw": data,
        }

    def find_instance_by_request_id(self, request_id: str) -> dict[str, Any] | None:
        """Locate a prior rental only when the provider exposes a trusted match."""

        if self.dry_run:
            return None
        raise VastClientError("Vast.ai request-id reconciliation is not verified for this provider profile")

    def get_instance_status(self, instance_id: str) -> dict[str, Any]:
        if self.dry_run:
            return {
                "instance_id": instance_id,
                "status": "running",
                "health_status": "healthy",
                "public_endpoint_url": "http://dry-run-vast.local:8000",
                "dry_run": True,
            }
        return self._request("GET", f"/instances/{instance_id}/")

    def destroy_instance(self, instance_id: str) -> dict[str, Any]:
        if self.dry_run:
            return {"instance_id": instance_id, "destroyed": True, "dry_run": True}
        try:
            return self._request("DELETE", f"/instances/{instance_id}/")
        except VastClientError as exc:
            if "404" in str(exc) or "not found" in str(exc).lower():
                return {"instance_id": instance_id, "destroyed": True, "already_missing": True}
            raise

    def _request(self, method: str, path: str, json: dict | None = None) -> dict[str, Any]:
        if not self.api_key:
            raise VastClientError("Vast.ai API key is not configured")
        try:
            response = httpx.request(
                method,
                f"{self.base_url}{path}",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json=json,
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPStatusError as exc:
            raise VastClientError(f"Vast.ai API returned {exc.response.status_code}") from exc
        except Exception as exc:
            raise VastClientError("Vast.ai API request failed") from exc
        if not isinstance(data, dict):
            raise VastClientError("Unexpected Vast.ai API response")
        return data


def select_offer(
    offers: list[VastOffer],
    settings: Settings,
) -> VastOffer | None:
    allowlist = set(_gpu_allowlist(settings))
    acceptable: list[VastOffer] = []
    for offer in offers:
        if offer.hourly_cost_usd > settings.vast_max_hourly_cost_usd:
            continue
        if allowlist and offer.gpu_name not in allowlist:
            continue
        if offer.gpu_ram_gb < settings.vast_min_gpu_ram_gb:
            continue
        if offer.disk_gb is not None and offer.disk_gb < settings.vast_disk_gb:
            continue
        if settings.vast_require_verified and offer.verified is False:
            continue
        if not offer.rentable:
            continue
        acceptable.append(offer)
    acceptable.sort(key=lambda item: item.hourly_cost_usd)
    return acceptable[0] if acceptable else None


def _offer_from_payload(payload: dict[str, Any]) -> VastOffer:
    gpu_name = str(
        payload.get("gpu_name")
        or payload.get("gpu")
        or payload.get("gpu_display_name")
        or payload.get("gpu_name_str")
        or "unknown"
    )
    return VastOffer(
        id=str(payload.get("id") or payload.get("ask_contract_id") or payload.get("bundle_id") or ""),
        gpu_name=gpu_name.replace(" ", "_"),
        hourly_cost_usd=float(payload.get("dph_total") or payload.get("hourly_cost_usd") or payload.get("price") or 0),
        gpu_ram_gb=float(payload.get("gpu_ram") or payload.get("gpu_ram_gb") or 0),
        disk_gb=float(payload["disk_space"]) if payload.get("disk_space") is not None else None,
        verified=payload.get("verified"),
        rentable=bool(payload.get("rentable", payload.get("available", True))),
        public_endpoint_url=payload.get("public_endpoint_url") or payload.get("url"),
        metadata=payload,
    )


def _gpu_allowlist(settings: Settings) -> list[str]:
    return [item.strip() for item in settings.vast_gpu_allowlist.split(",") if item.strip()]


def _first_allowed_gpu(settings: Settings) -> str:
    allowlist = _gpu_allowlist(settings)
    return allowlist[0] if allowlist else "RTX_4090"
