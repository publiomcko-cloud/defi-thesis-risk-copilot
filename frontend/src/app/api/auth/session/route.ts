import { NextResponse } from "next/server";

import { getApiBaseUrl } from "@/lib/api";
import { readSessionToken } from "@/lib/server-auth";

export async function GET() {
  const token = await readSessionToken();
  if (!token) {
    return NextResponse.json({ authenticated: false });
  }
  const response = await fetch(`${getApiBaseUrl()}/api/auth/me`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store"
  });
  if (!response.ok) {
    return NextResponse.json({ authenticated: false }, { status: 401 });
  }
  return NextResponse.json({ authenticated: true, user: await response.json() });
}
