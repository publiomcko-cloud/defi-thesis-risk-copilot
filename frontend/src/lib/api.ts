import type {
  AnalysisRequest,
  AnalysisResponse,
  DiscoveredItemsResponse,
  DiscoveryRunResponse,
  EvaluateDiscoveredItemResponse,
  HealthResponse,
  MarkdownExportResponse,
  MonitoringRunResponse,
  ProtocolListResponse,
  ReportResponse,
  ReviewItemsResponse,
  ReviewStatus,
  ReviewStatusUpdateResponse,
  IngestToRagResponse,
  SimulationRequest,
  SimulationResponse,
  WatchlistCreateResponse,
  WatchlistEvaluationResponse,
  WatchlistItemCreate,
  WatchlistItemUpdate,
  WatchlistItemsResponse,
  WatchlistUpdateResponse,
  AlertEventsResponse,
  AlertStatus,
  AlertStatusUpdateResponse,
  OptionsAnalysisRequest,
  OptionsAnalysisResponse,
  UserContext,
  ProviderCredentialCreateRequest,
  ProviderCredentialResponse,
  ProviderCredentialsResponse,
  ProviderCredentialUpdateRequest,
  AuditEventsResponse,
  DemoScenario,
  DemoSeedResult,
  DemoStatus,
  DeploymentStatus,
  VastCleanupResponse,
  VastConfig,
  VastSessionActionResponse,
  VastSessionListResponse,
  VastStartSessionRequest,
  VastTestPromptResponse,
  JobResponse
} from "./types";

export function getApiBaseUrl(): string {
  if (typeof window !== "undefined") {
    return "/api/backend";
  }
  return process.env.BACKEND_API_BASE_URL ?? process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";
}

export function getAuthToken(): string {
  return "";
}

export function setAuthToken(token: string): void {
  void token;
}

function authHeaders(): Record<string, string> {
  return {};
}

function requestInit(init: RequestInit = {}): RequestInit {
  return {
    ...init,
    credentials: "include"
  };
}

async function errorDetail(response: Response, fallback: string): Promise<string> {
  try {
    const payload = await response.json();
    return payload.detail ?? fallback;
  } catch {
    return fallback;
  }
}

export async function fetchCurrentUser(): Promise<UserContext> {
  const response = await fetch(`${getApiBaseUrl()}/api/auth/me`, {
    cache: "no-store",
    ...requestInit({ headers: authHeaders() })
  });

  if (!response.ok) {
    throw new Error(await errorDetail(response, `Current user fetch failed with status ${response.status}`));
  }

  return response.json();
}

export async function fetchHealth(): Promise<HealthResponse> {
  const response = await fetch(`${getApiBaseUrl()}/health`, {
    cache: "no-store"
  });

  if (!response.ok) {
    throw new Error(`Health check failed with status ${response.status}`);
  }

  return response.json();
}

export async function fetchDemoStatus(): Promise<DemoStatus> {
  const response = await fetch(`${getApiBaseUrl()}/api/demo/status`, {
    cache: "no-store"
  });

  if (!response.ok) {
    throw new Error(await errorDetail(response, `Demo status failed with status ${response.status}`));
  }

  return response.json();
}

export async function fetchDeploymentStatus(): Promise<DeploymentStatus> {
  const response = await fetch(`${getApiBaseUrl()}/api/deployment/status`, {
    cache: "no-store"
  });

  if (!response.ok) {
    throw new Error(await errorDetail(response, `Deployment status failed with status ${response.status}`));
  }

  return response.json();
}

export async function fetchDemoScenarios(): Promise<DemoScenario[]> {
  const response = await fetch(`${getApiBaseUrl()}/api/demo/scenarios`, {
    cache: "no-store"
  });

  if (!response.ok) {
    throw new Error(await errorDetail(response, `Demo scenarios failed with status ${response.status}`));
  }

  return response.json();
}

export async function seedDemoData(): Promise<DemoSeedResult> {
  const response = await fetch(`${getApiBaseUrl()}/api/demo/seed`, {
    method: "POST",
    headers: authHeaders()
  });

  if (!response.ok) {
    throw new Error(await errorDetail(response, `Demo seed failed with status ${response.status}`));
  }

  return response.json();
}

export async function fetchProtocols(): Promise<ProtocolListResponse> {
  const response = await fetch(`${getApiBaseUrl()}/api/protocols`, {
    cache: "no-store"
  });

  if (!response.ok) {
    throw new Error(`Protocol fetch failed with status ${response.status}`);
  }

  return response.json();
}

export async function analyzeStrategy(
  payload: AnalysisRequest,
  idempotencyKey?: string
): Promise<AnalysisResponse> {
  const response = await fetch(`${getApiBaseUrl()}/api/analyze`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(idempotencyKey ? { "Idempotency-Key": idempotencyKey } : {})
    },
    body: JSON.stringify(payload),
    ...requestInit()
  });

  if (!response.ok) {
    throw new Error(await errorDetail(response, `Analysis failed with status ${response.status}`));
  }

  return response.json();
}

export async function fetchJob(jobId: string): Promise<JobResponse> {
  const response = await fetch(`${getApiBaseUrl()}/api/jobs/${jobId}`, {
    cache: "no-store",
    ...requestInit({ headers: authHeaders() })
  });
  if (!response.ok) {
    throw new Error(await errorDetail(response, `Job fetch failed with status ${response.status}`));
  }
  return response.json();
}

export async function cancelJob(jobId: string): Promise<JobResponse> {
  const response = await fetch(`${getApiBaseUrl()}/api/jobs/${jobId}/cancel`, {
    method: "POST",
    ...requestInit({ headers: authHeaders() })
  });
  if (!response.ok) {
    throw new Error(await errorDetail(response, `Job cancellation failed with status ${response.status}`));
  }
  return response.json();
}

export async function fetchReport(reportId: string): Promise<ReportResponse> {
  const response = await fetch(`${getApiBaseUrl()}/api/reports/${reportId}`, {
    cache: "no-store"
  });

  if (!response.ok) {
    throw new Error(`Report fetch failed with status ${response.status}`);
  }

  return response.json();
}

export async function exportReportMarkdown(
  reportId: string
): Promise<MarkdownExportResponse> {
  const response = await fetch(`${getApiBaseUrl()}/api/reports/${reportId}/export`, {
    method: "POST"
  });

  if (!response.ok) {
    throw new Error(`Markdown export failed with status ${response.status}`);
  }

  return response.json();
}

export async function runSourceMonitoring(): Promise<MonitoringRunResponse> {
  const response = await fetch(`${getApiBaseUrl()}/api/monitoring/run`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({})
  });

  if (!response.ok) {
    throw new Error(`Monitoring run failed with status ${response.status}`);
  }

  return response.json();
}

export async function runDiscovery(): Promise<DiscoveryRunResponse> {
  const response = await fetch(`${getApiBaseUrl()}/api/discovery/run`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders()
    },
    body: JSON.stringify({
      include_defillama: true,
      auto_evaluate: true,
      evaluation_limit: 5
    })
  });

  if (!response.ok) {
    throw new Error(`Discovery run failed with status ${response.status}`);
  }

  return response.json();
}

export async function fetchDiscoveredItems(): Promise<DiscoveredItemsResponse> {
  const response = await fetch(`${getApiBaseUrl()}/api/discovery/candidates`, {
    cache: "no-store"
  });

  if (!response.ok) {
    throw new Error(`Discovered item fetch failed with status ${response.status}`);
  }

  return response.json();
}

export async function ingestReviewItemToRag(
  reviewItemId: string
): Promise<IngestToRagResponse> {
  const response = await fetch(
    `${getApiBaseUrl()}/api/evaluation/review-items/${reviewItemId}/ingest-to-rag`,
    {
      method: "POST",
      headers: authHeaders()
    }
  );

  if (!response.ok) {
    throw new Error(await errorDetail(response, `RAG ingestion failed with status ${response.status}`));
  }

  return response.json();
}

export async function evaluateDiscoveredItem(
  discoveredItemId: string
): Promise<EvaluateDiscoveredItemResponse> {
  const response = await fetch(
    `${getApiBaseUrl()}/api/evaluation/discovered-items/${discoveredItemId}/evaluate`,
    {
      method: "POST"
    }
  );

  if (!response.ok) {
    throw new Error(`Evaluation failed with status ${response.status}`);
  }

  return response.json();
}

export async function fetchReviewItems(): Promise<ReviewItemsResponse> {
  const response = await fetch(`${getApiBaseUrl()}/api/evaluation/review-items`, {
    cache: "no-store"
  });

  if (!response.ok) {
    throw new Error(`Review queue fetch failed with status ${response.status}`);
  }

  return response.json();
}

export async function updateReviewItemStatus(
  reviewItemId: string,
  status: ReviewStatus,
  reviewerNotes?: string
): Promise<ReviewStatusUpdateResponse> {
  const response = await fetch(
    `${getApiBaseUrl()}/api/evaluation/review-items/${reviewItemId}`,
    {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
        ...authHeaders()
      },
      body: JSON.stringify({
        status,
        reviewer_notes: reviewerNotes || null
      })
    }
  );

  if (!response.ok) {
    throw new Error(await errorDetail(response, `Review update failed with status ${response.status}`));
  }

  return response.json();
}

export async function createProviderCredential(
  payload: ProviderCredentialCreateRequest
): Promise<ProviderCredentialResponse> {
  const response = await fetch(`${getApiBaseUrl()}/api/admin/provider-credentials`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders()
    },
    body: JSON.stringify(payload)
  });

  if (!response.ok) {
    throw new Error(await errorDetail(response, `Credential creation failed with status ${response.status}`));
  }

  return response.json();
}

export async function fetchProviderCredentials(): Promise<ProviderCredentialsResponse> {
  const response = await fetch(`${getApiBaseUrl()}/api/admin/provider-credentials`, {
    cache: "no-store",
    headers: authHeaders()
  });

  if (!response.ok) {
    throw new Error(await errorDetail(response, `Credential fetch failed with status ${response.status}`));
  }

  return response.json();
}

export async function updateProviderCredential(
  credentialId: string,
  payload: ProviderCredentialUpdateRequest
): Promise<ProviderCredentialResponse> {
  const response = await fetch(`${getApiBaseUrl()}/api/admin/provider-credentials/${credentialId}`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders()
    },
    body: JSON.stringify(payload)
  });

  if (!response.ok) {
    throw new Error(await errorDetail(response, `Credential update failed with status ${response.status}`));
  }

  return response.json();
}

export async function disableProviderCredential(
  credentialId: string
): Promise<ProviderCredentialResponse> {
  const response = await fetch(`${getApiBaseUrl()}/api/admin/provider-credentials/${credentialId}`, {
    method: "DELETE",
    headers: authHeaders()
  });

  if (!response.ok) {
    throw new Error(await errorDetail(response, `Credential disable failed with status ${response.status}`));
  }

  return response.json();
}

export async function fetchAuditEvents(limit = 100): Promise<AuditEventsResponse> {
  const response = await fetch(`${getApiBaseUrl()}/api/admin/audit-events?limit=${limit}`, {
    cache: "no-store",
    headers: authHeaders()
  });

  if (!response.ok) {
    throw new Error(await errorDetail(response, `Audit event fetch failed with status ${response.status}`));
  }

  return response.json();
}

export async function fetchVastConfig(): Promise<VastConfig> {
  const response = await fetch(`${getApiBaseUrl()}/api/admin/vast/config`, {
    cache: "no-store",
    headers: authHeaders()
  });

  if (!response.ok) {
    throw new Error(await errorDetail(response, `Vast config fetch failed with status ${response.status}`));
  }

  return response.json();
}

export async function acknowledgeVastConfig(note: string): Promise<VastConfig> {
  const response = await fetch(`${getApiBaseUrl()}/api/admin/vast/config`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders()
    },
    body: JSON.stringify({ note })
  });

  if (!response.ok) {
    throw new Error(await errorDetail(response, `Vast config update failed with status ${response.status}`));
  }

  return response.json();
}

export async function startVastSession(
  payload: VastStartSessionRequest
): Promise<VastSessionActionResponse> {
  const response = await fetch(`${getApiBaseUrl()}/api/admin/vast/sessions/start`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders()
    },
    body: JSON.stringify(payload)
  });

  if (!response.ok) {
    throw new Error(await errorDetail(response, `Vast session start failed with status ${response.status}`));
  }

  return response.json();
}

export async function fetchVastSessions(): Promise<VastSessionListResponse> {
  const response = await fetch(`${getApiBaseUrl()}/api/admin/vast/sessions`, {
    cache: "no-store",
    headers: authHeaders()
  });

  if (!response.ok) {
    throw new Error(await errorDetail(response, `Vast sessions fetch failed with status ${response.status}`));
  }

  return response.json();
}

export async function testVastPrompt(
  sessionId: string,
  prompt: string
): Promise<VastTestPromptResponse> {
  const response = await fetch(`${getApiBaseUrl()}/api/admin/vast/sessions/${sessionId}/test-prompt`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders()
    },
    body: JSON.stringify({ prompt })
  });

  if (!response.ok) {
    throw new Error(await errorDetail(response, `Vast test prompt failed with status ${response.status}`));
  }

  return response.json();
}

export async function destroyVastSession(
  sessionId: string
): Promise<VastSessionActionResponse> {
  const response = await fetch(`${getApiBaseUrl()}/api/admin/vast/sessions/${sessionId}/destroy`, {
    method: "POST",
    headers: authHeaders()
  });

  if (!response.ok) {
    throw new Error(await errorDetail(response, `Vast destroy failed with status ${response.status}`));
  }

  return response.json();
}

export async function cleanupVastSessions(): Promise<VastCleanupResponse> {
  const response = await fetch(`${getApiBaseUrl()}/api/admin/vast/cleanup`, {
    method: "POST",
    headers: authHeaders()
  });

  if (!response.ok) {
    throw new Error(await errorDetail(response, `Vast cleanup failed with status ${response.status}`));
  }

  return response.json();
}

export async function runStrategySimulation(
  payload: SimulationRequest
): Promise<SimulationResponse> {
  const response = await fetch(`${getApiBaseUrl()}/api/simulation/run`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload)
  });

  if (!response.ok) {
    throw new Error(`Simulation failed with status ${response.status}`);
  }

  return response.json();
}

export async function createWatchlistItem(
  payload: WatchlistItemCreate
): Promise<WatchlistCreateResponse> {
  const response = await fetch(`${getApiBaseUrl()}/api/watchlist/items`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload)
  });

  if (!response.ok) {
    throw new Error(`Watchlist item creation failed with status ${response.status}`);
  }

  return response.json();
}

export async function fetchWatchlistItems(): Promise<WatchlistItemsResponse> {
  const response = await fetch(`${getApiBaseUrl()}/api/watchlist/items`, {
    cache: "no-store"
  });

  if (!response.ok) {
    throw new Error(`Watchlist fetch failed with status ${response.status}`);
  }

  return response.json();
}

export async function updateWatchlistItem(
  itemId: string,
  payload: WatchlistItemUpdate
): Promise<WatchlistUpdateResponse> {
  const response = await fetch(`${getApiBaseUrl()}/api/watchlist/items/${itemId}`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload)
  });

  if (!response.ok) {
    throw new Error(`Watchlist update failed with status ${response.status}`);
  }

  return response.json();
}

export async function evaluateWatchlistItem(
  itemId: string
): Promise<WatchlistEvaluationResponse> {
  const response = await fetch(
    `${getApiBaseUrl()}/api/watchlist/items/${itemId}/evaluate`,
    {
      method: "POST"
    }
  );

  if (!response.ok) {
    throw new Error(`Watchlist evaluation failed with status ${response.status}`);
  }

  return response.json();
}

export async function fetchAlertEvents(): Promise<AlertEventsResponse> {
  const response = await fetch(`${getApiBaseUrl()}/api/watchlist/alerts`, {
    cache: "no-store"
  });

  if (!response.ok) {
    throw new Error(`Alert fetch failed with status ${response.status}`);
  }

  return response.json();
}

export async function updateAlertStatus(
  alertId: string,
  status: AlertStatus
): Promise<AlertStatusUpdateResponse> {
  const response = await fetch(`${getApiBaseUrl()}/api/watchlist/alerts/${alertId}`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ status })
  });

  if (!response.ok) {
    throw new Error(`Alert update failed with status ${response.status}`);
  }

  return response.json();
}

export async function analyzeOption(
  payload: OptionsAnalysisRequest
): Promise<OptionsAnalysisResponse> {
  const response = await fetch(`${getApiBaseUrl()}/api/options/analyze`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload)
  });

  if (!response.ok) {
    throw new Error(`Options analysis failed with status ${response.status}`);
  }

  return response.json();
}
