import { NextResponse } from "next/server";

import { loadMfaState } from "@/lib/mfa-provider";
import {
  getValidAccessToken,
  jsonWithSessionCookies,
  supabaseAuthFetch
} from "@/lib/server-auth";

export async function GET() {
  const sessionResponse = NextResponse.json({});
  const token = await getValidAccessToken(sessionResponse);
  if (!token) {
    return jsonWithSessionCookies(sessionResponse, { detail: "Authentication required." }, 401);
  }

  const result = await loadMfaState(token, supabaseAuthFetch);
  if (!result.ok) {
    return jsonWithSessionCookies(
      sessionResponse,
      { detail: mfaFailureMessage(result.status) },
      result.status,
    );
  }
  return jsonWithSessionCookies(sessionResponse, result.data);
}

function mfaFailureMessage(status: number): string {
  if (status === 401) {
    return "Your session has expired. Log in again.";
  }
  if (status === 503) {
    return "MFA is unavailable because Supabase Auth is not configured.";
  }
  return "MFA status could not be loaded.";
}
