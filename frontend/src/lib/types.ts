export type HealthResponse = {
  status: "healthy";
  service: string;
  environment: string;
  timestamp: string;
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
