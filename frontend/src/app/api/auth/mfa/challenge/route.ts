import { NextRequest, NextResponse } from "next/server";

import { challengeAndVerifyTotp } from "@/lib/mfa-provider";
import { hasTrustedOrigin } from "@/lib/request-security";
import {
  getValidAccessToken,
  jsonWithSessionCookies,
  recordMfaAuditEvent,
  setSupabaseSessionCookies,
  supabaseAuthFetch
} from "@/lib/server-auth";

export async function POST(request: NextRequest) {
  if (!hasTrustedOrigin(request)) {
    return NextResponse.json({ detail: "Cross-origin request denied." }, { status: 403 });
  }
  const payload = await safeRequestJson(request);
  const sessionResponse = NextResponse.json({});
  const token = await getValidAccessToken(sessionResponse);
  if (!token) {
    return jsonWithSessionCookies(sessionResponse, { detail: "Authentication required." }, 401);
  }

  const result = await challengeAndVerifyTotp(
    token,
    typeof payload.factor_id === "string" ? payload.factor_id : "",
    typeof payload.code === "string" ? payload.code.trim() : "",
    supabaseAuthFetch,
  );
  if (!result.ok) {
    return jsonWithSessionCookies(
      sessionResponse,
      { detail: result.status === 400 ? "Enter a valid verification code." : "The verification code could not be confirmed." },
      result.status,
    );
  }

  await setSupabaseSessionCookies(sessionResponse, result.data);
  await recordMfaAuditEvent(token, "mfa.challenge_verified", typeof payload.factor_id === "string" ? payload.factor_id : undefined);
  return jsonWithSessionCookies(sessionResponse, { status: "verified", assurance_level: "aal2" });
}

async function safeRequestJson(request: NextRequest): Promise<Record<string, unknown>> {
  try {
    const payload = await request.json();
    return payload && typeof payload === "object" ? payload : {};
  } catch {
    return {};
  }
}
