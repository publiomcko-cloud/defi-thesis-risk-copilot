import type {
  AnalysisRequest,
  AnalysisResponse,
  HealthResponse,
  MarkdownExportResponse,
  ProtocolListResponse,
  ReportResponse
} from "./types";

export function getApiBaseUrl(): string {
  return process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";
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
  payload: AnalysisRequest
): Promise<AnalysisResponse> {
  const response = await fetch(`${getApiBaseUrl()}/api/analyze`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload)
  });

  if (!response.ok) {
    throw new Error(`Analysis failed with status ${response.status}`);
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
