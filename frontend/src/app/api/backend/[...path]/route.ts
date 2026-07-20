import { NextRequest, NextResponse } from "next/server";

import { backendApiBaseUrl, getValidAccessToken } from "@/lib/server-auth";

const ALLOWED_PREFIXES = ["/", "/health", "/ready", "/api/"];

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
  if (!ALLOWED_PREFIXES.some((prefix) => targetPath === prefix || targetPath.startsWith(prefix))) {
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
  const incomingCookie = request.headers.get("cookie");
  if (incomingCookie) {
    headers.set("cookie", incomingCookie);
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
  const proxied = new NextResponse(body, {
    status: backendResponse.status,
    headers: {
      "content-type": backendResponse.headers.get("content-type") ?? "application/json"
    }
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
