from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class PrivacyPreferenceUpdateRequest(BaseModel):
    purpose: Literal["product_improvement"] = "product_improvement"
    enabled: bool

    model_config = ConfigDict(extra="forbid")


class PrivacyPreferenceResponse(BaseModel):
    purpose: Literal["product_improvement"] = "product_improvement"
    enabled: bool = False
    policy_version: str
    collection_enabled: bool = False
    requires_reconsent: bool = False
    updated_at: datetime | None = None


class PrivacyPreferencesResponse(BaseModel):
    items: list[PrivacyPreferenceResponse]


class PrivacyPreferenceUpdateResponse(BaseModel):
    preference: PrivacyPreferenceResponse
    decision: Literal["grant", "deny", "withdraw"]
    duplicate: bool = False
