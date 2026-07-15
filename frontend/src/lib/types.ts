export type HealthResponse = {
  status: "healthy";
  service: string;
  environment: string;
  timestamp: string;
};

export type UserRole = "admin" | "common";

export type UserContext = {
  id: string;
  email: string;
  role: UserRole;
  is_active: boolean;
  auth_enabled: boolean;
};

export type ProviderName =
  | "openai_compatible"
  | "coingecko"
  | "defillama_pro"
  | "vast_ai";

export type ProviderCredentialCreateRequest = {
  provider: ProviderName;
  name: string;
  secret: string;
  enabled: boolean;
};

export type ProviderCredentialUpdateRequest = {
  name?: string;
  secret?: string;
  enabled?: boolean;
};

export type ProviderCredentialMetadata = {
  id: string;
  provider: ProviderName | string;
  name: string;
  secret_last4: string;
  enabled: boolean;
  created_by: string;
  created_at: string;
  updated_at: string;
  last_used_at?: string | null;
};

export type ProviderCredentialsResponse = {
  items: ProviderCredentialMetadata[];
};

export type ProviderCredentialResponse = {
  credential: ProviderCredentialMetadata;
};

export type AuditEvent = {
  id: string;
  actor_user_id?: string | null;
  action: string;
  resource_type: string;
  resource_id?: string | null;
  metadata_json: Record<string, unknown>;
  created_at: string;
};

export type AuditEventsResponse = {
  items: AuditEvent[];
};

export type VastConfig = {
  enabled: boolean;
  dry_run: boolean;
  api_base_url: string;
  credential_name: string;
  has_env_api_key: boolean;
  max_hourly_cost_usd: number;
  max_session_minutes: number;
  max_active_instances: number;
  gpu_allowlist: string[];
  min_gpu_ram_gb: number;
  disk_gb: number;
  require_verified: boolean;
  auto_destroy: boolean;
  idle_timeout_seconds: number;
  image: string;
  model: string;
  container_port: number;
  startup_timeout_seconds: number;
  poll_interval_seconds: number;
};

export type VastSession = {
  id: string;
  status: string;
  provider: string;
  vast_instance_id?: string | null;
  vast_contract_id?: string | null;
  offer_id?: string | null;
  model: string;
  image: string;
  gpu_name?: string | null;
  hourly_cost_usd?: number | null;
  max_runtime_minutes: number;
  container_port: number;
  public_endpoint_url?: string | null;
  health_status?: string | null;
  last_error?: string | null;
  created_by: string;
  created_at: string;
  ready_at?: string | null;
  last_used_at?: string | null;
  destroyed_at?: string | null;
  cleanup_attempted_at?: string | null;
  metadata_json: Record<string, unknown>;
};

export type VastSessionActionResponse = {
  session: VastSession;
};

export type VastSessionListResponse = {
  items: VastSession[];
};

export type VastStartSessionRequest = {
  model?: string;
  image?: string;
  allow_remote_gpu: boolean;
  warm_instance: boolean;
};

export type VastTestPromptResponse = {
  session: VastSession;
  output: string;
  provider: string;
  model: string;
};

export type VastCleanupResponse = {
  cleaned_count: number;
  failed_count: number;
  sessions: VastSession[];
};

export type DemoScenario = {
  id: string;
  title: string;
  summary: string;
  primary_path: string;
  report_id?: string | null;
  tags: string[];
  safety_note: string;
};

export type DemoStatus = {
  seeded: boolean;
  counts: Record<string, number>;
  report_ids: string[];
  scenarios: DemoScenario[];
};

export type DemoSeedResult = {
  status: "seeded";
  seeded: boolean;
  counts: Record<string, number>;
  report_ids: string[];
  scenario_ids: string[];
  message: string;
};

export type AnalysisDepth = "quick" | "standard" | "deep";

export type RiskRating =
  | "Conservative"
  | "Moderate"
  | "Aggressive"
  | "Very Risky";

export type ManualInputs = {
  borrow_apy?: number;
  implied_apy?: number;
  liquidity_usd?: number;
  ltv?: number;
  lltv?: number;
  collateral_asset?: string;
  debt_asset?: string;
  pt_price?: number;
  maturity_date?: string;
  token_id?: string;
  supply_apy?: number;
  liquidation_threshold?: number;
  reserve_asset?: string;
};

export type AnalysisRequest = {
  strategy_description: string;
  protocols: string[];
  market_url?: string | null;
  manual_inputs: ManualInputs;
  analysis_depth: AnalysisDepth;
};

export type AnalysisResponse = {
  report_id: string;
  status: "completed";
  risk_rating: RiskRating;
  summary: string;
};

export type Protocol = {
  id: string;
  name: string;
  category: string;
  supported_in_mvp: boolean;
  description: string;
};

export type ProtocolListResponse = {
  protocols: Protocol[];
};

export type SourceReference = {
  title: string;
  source_type: string;
  url?: string | null;
  protocol?: string | null;
};

export type ReportSection = {
  title: string;
  content: string;
};

export type ReportResponse = {
  report_id: string;
  status: "completed";
  risk_rating: RiskRating;
  executive_summary: string;
  strategy_description: string;
  protocols: string[];
  assumptions: string[];
  missing_data: string[];
  sections: ReportSection[];
  sources: SourceReference[];
  disclaimer: string;
};

export type MarkdownExportResponse = {
  report_id: string;
  filename: string;
  markdown: string;
};

export type ReviewStatus =
  | "needs_review"
  | "approved_for_rag"
  | "rejected"
  | "needs_more_data"
  | "archived";

export type DiscoveredItem = {
  id: string;
  source: string;
  source_type: string;
  title: string;
  url?: string | null;
  protocol?: string | null;
  chain?: string | null;
  asset?: string | null;
  market_identifier?: string | null;
  discovered_at: string;
  last_seen_at: string;
  raw_payload: Record<string, unknown>;
  status: ReviewStatus;
};

export type DiscoveredItemsResponse = {
  items: DiscoveredItem[];
};

export type DiscoveryRunResponse = {
  status: "completed" | "partial";
  created_count: number;
  duplicate_count: number;
  evaluated_count: number;
  failed_count: number;
  failures: Array<{
    source: string;
    error: string;
  }>;
  candidates: DiscoveredItem[];
};

export type MonitoringRunResponse = {
  status: "completed" | "partial";
  watches_checked: number;
  created_count: number;
  duplicate_count: number;
  failed_count: number;
  failures: Array<{
    source_watch_id: string;
    source: string;
    error: string;
  }>;
  discovered_items: DiscoveredItem[];
};

export type EvaluationResult = {
  id: string;
  discovered_item_id: string;
  report_id: string;
  risk_rating: string;
  risk_score: number;
  confidence: string;
  risk_summary: string;
  missing_data: string[];
  sources: Record<string, unknown>[];
  created_at: string;
};

export type ReviewItem = {
  id: string;
  discovered_item_id: string;
  evaluation_result_id: string;
  status: ReviewStatus;
  reviewer_notes?: string | null;
  prepared_for_rag: boolean;
  knowledge_base_ingestion?: {
    id: string;
    generated_markdown_path: string;
    ingested_at: string;
    ingested_by: string;
    status: string;
  } | null;
  created_at: string;
  updated_at: string;
  discovered_item: {
    id: string;
    source: string;
    source_type: string;
    title: string;
    url?: string | null;
    protocol?: string | null;
    chain?: string | null;
    asset?: string | null;
    market_identifier?: string | null;
    status: ReviewStatus;
  };
  evaluation_result: EvaluationResult;
};

export type ReviewItemsResponse = {
  items: ReviewItem[];
};

export type EvaluateDiscoveredItemResponse = {
  status: "completed";
  evaluation_result: EvaluationResult;
  review_item: ReviewItem;
};

export type ReviewStatusUpdateResponse = {
  review_item: ReviewItem;
};

export type IngestToRagResponse = {
  status: "ingested";
  ingestion: {
    id: string;
    review_item_id: string;
    generated_markdown_path: string;
    ingested_at: string;
    ingested_by: string;
    source_url?: string | null;
    protocol?: string | null;
    status: string;
  };
  refreshed_chunk_count: number;
};

export type SimulationRequest = {
  strategy_description?: string;
  protocols: string[];
  implied_apy?: number;
  supply_apy?: number;
  incentive_apy?: number;
  borrow_apy?: number;
  ltv?: number;
  lltv?: number;
  collateral_value_usd?: number;
  debt_value_usd?: number;
  liquidity_usd?: number;
  pt_price?: number;
  maturity_date?: string;
  borrow_apy_shock_multiplier?: number;
  liquidity_shock_pct?: number;
  collateral_drawdown_pct?: number;
  early_exit_discount_pct?: number;
  slippage_bps?: number;
};

export type SimulationScenario = {
  name: string;
  scenario_type:
    | "net_spread"
    | "borrow_apy_shock"
    | "liquidity_slippage_shock"
    | "collateral_drawdown"
    | "early_exit"
    | "incentive_removal"
    | "combined_adverse";
  result: Record<string, number | string | null>;
  formula: string;
  assumptions: string[];
  missing_data: string[];
  interpretation: string;
};

export type SimulationResponse = {
  status: "completed" | "partial";
  scenarios: SimulationScenario[];
  assumptions: string[];
  missing_data: string[];
  disclaimer: string;
};

export type WatchlistItemType = "strategy" | "protocol" | "market" | "discovered_item";
export type AlertStatus = "open" | "acknowledged" | "archived";

export type WatchlistItemCreate = {
  item_type: WatchlistItemType;
  title: string;
  protocol?: string;
  market_identifier?: string;
  source_url?: string;
  rules: Record<string, number | boolean>;
  snapshot: Record<string, number | boolean | string>;
};

export type WatchlistItemUpdate = {
  rules?: Record<string, number | boolean>;
  snapshot?: Record<string, number | boolean | string>;
  enabled?: boolean;
};

export type WatchlistItem = {
  id: string;
  item_type: WatchlistItemType;
  title: string;
  protocol?: string | null;
  market_identifier?: string | null;
  source_url?: string | null;
  rules: Record<string, unknown>;
  snapshot: Record<string, unknown>;
  enabled: boolean;
  created_at: string;
  last_evaluated_at?: string | null;
};

export type AlertEvent = {
  id: string;
  watchlist_item_id: string;
  alert_type: string;
  severity: "info" | "warning" | "critical";
  title: string;
  message: string;
  trigger_value?: number | null;
  threshold_value?: number | null;
  status: AlertStatus;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type WatchlistItemsResponse = {
  items: WatchlistItem[];
};

export type WatchlistCreateResponse = {
  item: WatchlistItem;
};

export type WatchlistUpdateResponse = {
  item: WatchlistItem;
};

export type WatchlistEvaluationResponse = {
  status: "completed";
  watchlist_item: WatchlistItem;
  created_alerts: AlertEvent[];
  evaluated_rules: string[];
};

export type AlertEventsResponse = {
  items: AlertEvent[];
};

export type AlertStatusUpdateResponse = {
  alert: AlertEvent;
};

export type OptionType = "call" | "put";

export type OptionsAnalysisRequest = {
  option_type: OptionType;
  underlying_asset: string;
  underlying_price: number;
  strike_price: number;
  premium: number;
  expiration_date?: string;
  implied_volatility?: number;
  bid?: number;
  ask?: number;
  contracts?: number;
  scenario_prices: number[];
  volatility_thesis?: string;
};

export type OptionScenario = {
  underlying_price: number;
  intrinsic_value: number;
  payoff: number;
  return_on_premium_pct?: number | null;
  moneyness: string;
};

export type OptionsAnalysisResponse = {
  option_type: OptionType;
  underlying_asset: string;
  breakeven_price: number;
  max_loss: number;
  max_profit: string;
  bid_ask_spread?: number | null;
  bid_ask_spread_pct?: number | null;
  days_to_expiration?: number | null;
  scenarios: OptionScenario[];
  assumptions: string[];
  risks: string[];
  missing_data: string[];
  volatility_summary: string;
  disclaimer: string;
};
