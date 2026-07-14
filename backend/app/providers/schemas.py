from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


ProviderName = Literal["openai_compatible", "coingecko", "defillama_pro", "vast_ai"]


class ProviderCredentialCreateRequest(BaseModel):
    provider: ProviderName
    name: str = Field(min_length=1, max_length=255)
    secret: str = Field(min_length=1, max_length=5000)
    enabled: bool = True


class ProviderCredentialUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    secret: str | None = Field(default=None, min_length=1, max_length=5000)
    enabled: bool | None = None


class ProviderCredentialMetadata(BaseModel):
    id: str
    provider: ProviderName | str
    name: str
    secret_last4: str
    enabled: bool
    created_by: str
    created_at: datetime
    updated_at: datetime
    last_used_at: datetime | None = None


class ProviderCredentialsResponse(BaseModel):
    items: list[ProviderCredentialMetadata]


class ProviderCredentialResponse(BaseModel):
    credential: ProviderCredentialMetadata
