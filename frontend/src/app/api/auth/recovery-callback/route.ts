import { NextRequest, NextResponse } from "next/server";

import { setSupabaseSessionCookies, supabaseAuthFetch } from "@/lib/server-auth";

const DEFAULT_RESET_PATH = "/reset-password";

export async function GET(request: NextRequest) {
  const code = request.nextUrl.searchParams.get("code") ?? "";
  const next = safeRedirectPath(request.nextUrl.searchParams.get("next"));
  if (!code) {
    return NextResponse.redirect(new URL(`${DEFAULT_RESET_PATH}?error=invalid_recovery_link`, request.url));
  }

  const exchange = await supabaseAuthFetch("/token?grant_type=pkce", {
    method: "POST",
    body: JSON.stringify({ auth_code: code })
  });
  const body = await exchange.json();
  if (!exchange.ok) {
    const response = NextResponse.redirect(new URL(`${DEFAULT_RESET_PATH}?error=expired_recovery_link`, request.url));
    return response;
  }

  const response = NextResponse.redirect(new URL(next, request.url));
  await setSupabaseSessionCookies(response, body);
  return response;
}

function safeRedirectPath(value: string | null): string {
  if (!value || !value.startsWith("/") || value.startsWith("//") || value.includes("..")) {
    return DEFAULT_RESET_PATH;
  }
  return value;
}
