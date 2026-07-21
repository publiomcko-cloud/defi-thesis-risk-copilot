import { NextRequest, NextResponse } from "next/server";

import { unenrollMfaFactor } from "@/lib/mfa-provider";
import { hasTrustedOrigin } from "@/lib/request-security";
import {
  getValidAccessToken,
  jsonWithSessionCookies,
  supabaseAuthFetch
} from "@/lib/server-auth";

export async function DELETE(
  request: NextRequest,
  context: { params: Promise<{ factorId: string }> },
) {
  if (!hasTrustedOrigin(request)) {
    return NextResponse.json({ detail: "Cross-origin request denied." }, { status: 403 });
  }
  const sessionResponse = NextResponse.json({});
  const token = await getValidAccessToken(sessionResponse);
  if (!token) {
    return jsonWithSessionCookies(sessionResponse, { detail: "Authentication required." }, 401);
  }

  const { factorId } = await context.params;
  const result = await unenrollMfaFactor(token, factorId, supabaseAuthFetch);
  if (!result.ok) {
    const detail = result.status === 400
      ? "Invalid MFA factor."
      : result.status === 403
        ? "Verify this session with MFA before removing a factor."
        : "The MFA factor could not be removed.";
    return jsonWithSessionCookies(sessionResponse, { detail }, result.status);
  }
  return jsonWithSessionCookies(sessionResponse, { status: "unenrolled" });
}
