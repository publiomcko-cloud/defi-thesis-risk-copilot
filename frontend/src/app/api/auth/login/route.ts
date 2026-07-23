import { NextResponse } from "next/server";

import { setSupabaseSessionCookies, supabaseAuthFetch } from "@/lib/server-auth";

export async function POST(request: Request) {
  const payload = await request.json();
  const response = await supabaseAuthFetch("/token?grant_type=password", {
    method: "POST",
    body: JSON.stringify({
      email: payload.email,
      password: payload.password
    })
  });
  const body = await response.json();
  if (!response.ok) {
    return NextResponse.json({ detail: "Login failed." }, { status: response.status });
  }
  const hasVerifiedFactor = Array.isArray(body?.user?.factors)
    && body.user.factors.some((factor: unknown) => (
      factor !== null
      && typeof factor === "object"
      && (factor as Record<string, unknown>).status === "verified"
    ));
  const nextPath = hasVerifiedFactor || process.env.ADMIN_MFA_REQUIRED === "true"
    ? "/account/security"
    : "/account";
  const result = NextResponse.json({ status: "authenticated", next: nextPath });
  await setSupabaseSessionCookies(result, body);
  return result;
}
