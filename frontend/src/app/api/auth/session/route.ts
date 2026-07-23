import { NextResponse } from "next/server";

import { backendApiBaseUrl, getValidAccessToken } from "@/lib/server-auth";

export async function GET() {
  const result = NextResponse.json({ authenticated: false });
  const token = await getValidAccessToken(result);
  if (!token) {
    return result;
  }
  const response = await fetch(`${backendApiBaseUrl()}/api/auth/me`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store"
  });
  if (!response.ok) {
    return result;
  }
  const body = await response.json();
  return NextResponse.json({ authenticated: true, user: body }, { headers: result.headers });
}
