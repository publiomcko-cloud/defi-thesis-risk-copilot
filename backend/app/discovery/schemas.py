from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.monitoring.schemas import DiscoveredItem


class DiscoveryFilters(BaseModel):
    min_tvl_usd: float | None = Field(default=10_000_000, ge=0)
    min_pool_tvl_usd: float | None = Field(default=1_000_000, ge=0)
    chain_allowlist: list[str] = Field(default_factory=lambda: ["ethereum", "arbitrum", "optimism", "base"])
    category_allowlist: list[str] = Field(default_factory=list)
    protocol_allowlist: list[str] = Field(default_factory=list)
    protocol_blocklist: list[str] = Field(default_factory=list)
    new_since_days: int | None = Field(default=None, ge=1)
    include_yield_pools: bool = True
    include_options_protocols: bool = True
    include_open_interest: bool = True
    include_fee_protocols: bool = True


class ManualDiscoveryItem(BaseModel):
    title: str
    url: str | None = None
    protocol: str | None = None
    chain: str | None = None
    source_type: str = "manual_source"
    asset: str | None = None
    market_identifier: str | None = None
    raw_payload: dict[str, Any] = Field(default_factory=dict)


class DiscoveryRunRequest(BaseModel):
    filters: DiscoveryFilters = Field(default_factory=DiscoveryFilters)
    manual_items: list[ManualDiscoveryItem] = Field(default_factory=list)
    include_defillama: bool = True
    auto_evaluate: bool = True
    evaluation_limit: int = Field(default=5, ge=0, le=25)


class DiscoveryFailure(BaseModel):
    source: str
    error: str


class DiscoveryRunResponse(BaseModel):
    status: Literal["completed", "partial"]
    created_count: int
    duplicate_count: int
    evaluated_count: int
    failed_count: int
    failures: list[DiscoveryFailure]
    candidates: list[DiscoveredItem]


class KnowledgeBaseIngestionRecord(BaseModel):
    id: str
    review_item_id: str
    generated_markdown_path: str
    ingested_at: datetime
    ingested_by: str
    source_url: str | None = None
    protocol: str | None = None
    status: str


class DiscoveredKnowledgeBaseResponse(BaseModel):
    items: list[KnowledgeBaseIngestionRecord]


class IngestToRagResponse(BaseModel):
    status: Literal["ingested"]
    ingestion: KnowledgeBaseIngestionRecord
    refreshed_chunk_count: int
