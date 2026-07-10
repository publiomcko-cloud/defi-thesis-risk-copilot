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
  protocols: string[];
  assumptions: string[];
  missing_data: string[];
  sections: ReportSection[];
  sources: SourceReference[];
  disclaimer: string;
};
