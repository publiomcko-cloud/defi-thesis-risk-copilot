import { NextResponse } from "next/server";

import { supabaseAuthFetch } from "@/lib/server-auth";

export async function POST(request: Request) {
  const payload = await request.json();
  const response = await supabaseAuthFetch("/signup", {
    method: "POST",
    body: JSON.stringify({
      email: payload.email,
      password: payload.password,
      data: {
        accepted_terms_version: payload.terms_version ?? "2026-07-20",
        accepted_privacy_version: payload.privacy_version ?? "2026-07-20"
      }
    })
  });
  if (!response.ok) {
    return NextResponse.json({ detail: "Signup failed." }, { status: response.status });
  }
  return NextResponse.json({
    status: "verification_required",
    message: "Check your email to verify your account before logging in."
  });
}
