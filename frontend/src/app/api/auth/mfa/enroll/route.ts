import { NextRequest, NextResponse } from "next/server";

import { enrollTotpFactor } from "@/lib/mfa-provider";
import { hasTrustedOrigin } from "@/lib/request-security";
import {
  getValidAccessToken,
  jsonWithSessionCookies,
  recordMfaAuditEvent,
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

  const result = await enrollTotpFactor(
    token,
    typeof payload.friendly_name === "string" ? payload.friendly_name : "Authenticator app",
    supabaseAuthFetch,
  );
  if (!result.ok) {
    return jsonWithSessionCookies(
      sessionResponse,
      { detail: result.status === 400 ? "Enter a valid authenticator name." : "MFA enrollment could not be started." },
      result.status,
    );
  }
  await recordMfaAuditEvent(token, "mfa.enrollment_started", result.data.factor_id);
  return jsonWithSessionCookies(sessionResponse, result.data);
}

async function safeRequestJson(request: NextRequest): Promise<Record<string, unknown>> {
  try {
    const payload = await request.json();
    return payload && typeof payload === "object" ? payload : {};
  } catch {
    return {};
  }
}
