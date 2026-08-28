import { NextRequest, NextResponse } from "next/server";
import { randomUUID } from "node:crypto";
import { isIP } from "node:net";

import { ANONYMOUS_COOKIE, backendApiBaseUrl, getValidAccessToken } from "@/lib/server-auth";
import { bffBodyLimit, readBodyWithinLimit } from "@/lib/request-body-limit";
import { hasTrustedOrigin } from "@/lib/request-security";

const ALLOWED_EXACT_PATHS = [
  "/health",
  "/ready",
  "/api/analyze",
  "/api/account",
  "/api/auth/me",
  "/api/consents",
  "/api/demo/scenarios",
  "/api/demo/seed",
  "/api/demo/status",
  "/api/deployment/status",
  "/api/discovery/candidates",
  "/api/discovery/run",
  "/api/jobs",
  "/api/knowledge/readiness",
  "/api/knowledge/sources",
  "/api/monitoring/run",
  "/api/notifications",
  "/api/notifications/mark-all-read",
  "/api/notifications/preferences",
  "/api/notifications/unread-count",
  "/api/options/analyze",
  "/api/organization-invitations/accept",
  "/api/organizations",
  "/api/protocols",
  "/api/schedules",
  "/api/simulation/run",
  "/api/theses",
  "/api/usage",
  "/api/watchlist/alerts",
  "/api/watchlist/items",
];
const ALLOWED_PREFIXES = [
  "/api/account/",
  "/api/admin/",
  "/api/evaluation/",
  "/api/jobs/",
  "/api/knowledge/",
  "/api/notifications/",
  "/api/organizations/",
  "/api/reports/",
  "/api/schedules/",
  "/api/theses/",
  "/api/watchlist/",
];
const SAFE_RESPONSE_HEADERS = [
  "content-type",
  "retry-after",
  "x-request-id",
  "x-correlation-id",
  "x-ratelimit-mode",
  "x-ratelimit-policy",
  "x-ratelimit-remaining",
  "x-ratelimit-reset"
];
const CORRELATION_ID_PATTERN = /^[A-Za-z0-9][A-Za-z0-9._:-]{7,127}$/;
const CUSTOMER_REQUEST_DETAIL_PATH = /^\/api\/customer-requests\/[A-Za-z0-9_-]+(?:\/close)?$/;
const UNSAFE_METHODS = new Set(["POST", "PUT", "PATCH", "DELETE"]);

export async function GET(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  return forward(request, context);
}

export async function POST(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  return forward(request, context);
}

export async function PATCH(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  return forward(request, context);
}

export async function PUT(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  return forward(request, context);
}

export async function DELETE(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  return forward(request, context);
}

async function forward(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  if (UNSAFE_METHODS.has(request.method) && !hasTrustedOrigin(request)) {
    return NextResponse.json({ detail: "Browser origin is not allowed." }, { status: 403 });
  }
  const params = await context.params;
  const targetPath = `/${params.path.join("/")}`;
  if (!isAllowedBackendPath(targetPath) || !isAllowedBackendMethod(targetPath, request.method)) {
    return NextResponse.json({ detail: "Unsupported backend path." }, { status: 404 });
  }
  const bodyResult = request.method === "GET" || request.method === "HEAD"
    ? { ok: true as const, body: undefined }
    : await readBodyWithinLimit(request, bffBodyLimit(targetPath));
  if (!bodyResult.ok) {
    return NextResponse.json({ detail: bodyResult.detail }, { status: bodyResult.status });
  }

  const responseShell = NextResponse.json({});
  const token = await getValidAccessToken(responseShell);
  let target: URL;
  let backendOrigin: string;
  try {
    backendOrigin = backendApiBaseUrl();
    target = new URL(targetPath, `${backendOrigin}/`);
  } catch {
    return NextResponse.json({ detail: "Backend service is unavailable." }, { status: 503 });
  }
  if (target.origin !== backendOrigin || target.pathname !== targetPath) {
    return NextResponse.json({ detail: "Unsupported backend path." }, { status: 404 });
  }
  target.search = request.nextUrl.search;

  const headers = new Headers();
  const correlationId = normalizeCorrelationId(request.headers.get("x-correlation-id"));
  headers.set("x-correlation-id", correlationId);
  headers.set("x-request-id", correlationId);
  const clientIp = normalizedClientIp(request);
  if (clientIp) {
    headers.set("x-forwarded-for", clientIp);
  }
  const contentType = request.headers.get("content-type");
  if (contentType) {
    headers.set("content-type", contentType);
  }
  const idempotencyKey = request.headers.get("idempotency-key");
  if (idempotencyKey) {
    headers.set("idempotency-key", idempotencyKey);
  }
  const anonymousCookie = request.cookies.get(ANONYMOUS_COOKIE)?.value;
  if (anonymousCookie) {
    headers.set("cookie", `${ANONYMOUS_COOKIE}=${encodeURIComponent(anonymousCookie)}`);
  }
  if (token) {
    headers.set("authorization", `Bearer ${token}`);
  }

  let backendResponse: Response;
  try {
    backendResponse = await fetch(target, {
      method: request.method,
      headers,
      body: bodyResult.body,
      cache: "no-store",
      redirect: "manual"
    });
  } catch {
    return NextResponse.json({ detail: "Backend service is unavailable." }, { status: 503 });
  }
  if (backendResponse.status >= 300 && backendResponse.status < 400) {
    return NextResponse.json({ detail: "Backend redirect rejected." }, { status: 502 });
  }
  const body = await backendResponse.text();
  const responseHeaders = new Headers();
  for (const header of SAFE_RESPONSE_HEADERS) {
    const value = backendResponse.headers.get(header);
    if (value) {
      responseHeaders.set(header, value);
    }
  }
  if (!responseHeaders.has("content-type")) {
    responseHeaders.set("content-type", "application/json");
  }
  const proxied = new NextResponse(body, {
    status: backendResponse.status,
    headers: responseHeaders
  });
  for (const cookie of responseShell.headers.getSetCookie?.() ?? []) {
    proxied.headers.append("set-cookie", cookie);
  }
  const backendCookie = backendResponse.headers.get("set-cookie");
  if (backendCookie) {
    proxied.headers.append("set-cookie", backendCookie);
  }
  return proxied;
}

function isAllowedBackendPath(path: string): boolean {
  if (!path.startsWith("/") || path.includes("..") || path.includes("//")) {
    return false;
  }
  try {
    const decodedPath = decodeURIComponent(path);
    if (decodedPath.includes("..") || decodedPath.includes("//") || decodedPath.includes("\\")) {
      return false;
    }
  } catch {
    return false;
  }
  if (path.startsWith("/internal/")) {
    return false;
  }
  if (path === "/api/customer-requests") {
    return true;
  }

  if (path.startsWith("/api/customer-requests/")) {
    return isCustomerRequestPath(path);
  }
  return ALLOWED_EXACT_PATHS.includes(path) || ALLOWED_PREFIXES.some((prefix) => path.startsWith(prefix));
}

function isAllowedBackendMethod(path: string, method: string): boolean {
  if (path === "/api/customer-requests") {
    return method === "GET" || method === "POST";
  }
  if (!isCustomerRequestPath(path)) {
    return true;
  }
  if (path.endsWith("/close")) {
    return method === "POST";
  }
  return method === "GET";
}

function isCustomerRequestPath(path: string): boolean {
  return CUSTOMER_REQUEST_DETAIL_PATH.test(path);
}

function normalizeCorrelationId(value: string | null): string {
  const candidate = value?.trim() ?? "";
  return CORRELATION_ID_PATTERN.test(candidate) ? candidate : `bff_${randomUUID().replaceAll("-", "")}`;
}

function normalizedClientIp(request: NextRequest): string | null {
  // Vercel injects this header at its trusted edge. Local and self-hosted BFFs
  // intentionally forward no caller IP until an explicit trusted integration
  // is added; browser-provided X-Forwarded-For is never accepted here.
  if (process.env.VERCEL !== "1") return null;
  const forwarded = request.headers.get("x-vercel-forwarded-for");
  const candidate = forwarded?.split(",", 1)[0].trim() ?? "";
  return isIP(candidate) ? candidate : null;
}
