import { NextRequest, NextResponse } from "next/server";

import { ANONYMOUS_COOKIE, backendApiBaseUrl, getValidAccessToken } from "@/lib/server-auth";

const ALLOWED_EXACT_PATHS = ["/health", "/ready"];
const ALLOWED_PREFIXES = ["/api/"];
const SAFE_RESPONSE_HEADERS = ["content-type", "x-request-id"];

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
  const params = await context.params;
  const targetPath = `/${params.path.join("/")}`;
  if (!isAllowedBackendPath(targetPath)) {
    return NextResponse.json({ detail: "Unsupported backend path." }, { status: 404 });
  }

  const responseShell = NextResponse.json({});
  const token = await getValidAccessToken(responseShell);
  const target = new URL(`${backendApiBaseUrl()}${targetPath}`);
  target.search = request.nextUrl.search;

  const headers = new Headers();
  const contentType = request.headers.get("content-type");
  if (contentType) {
    headers.set("content-type", contentType);
  }
  const anonymousCookie = request.cookies.get(ANONYMOUS_COOKIE)?.value;
  if (anonymousCookie) {
    headers.set("cookie", `${ANONYMOUS_COOKIE}=${encodeURIComponent(anonymousCookie)}`);
  }
  if (token) {
    headers.set("authorization", `Bearer ${token}`);
  }

  const backendResponse = await fetch(target, {
    method: request.method,
    headers,
    body: request.method === "GET" || request.method === "HEAD" ? undefined : await request.text(),
    cache: "no-store",
    redirect: "manual"
  });
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
  return ALLOWED_EXACT_PATHS.includes(path) || ALLOWED_PREFIXES.some((prefix) => path.startsWith(prefix));
}
