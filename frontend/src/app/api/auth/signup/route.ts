import { NextResponse } from "next/server";

import { supabaseAuthFetch } from "@/lib/server-auth";

export async function POST(request: Request) {
  const payload = await request.json();
  const response = await supabaseAuthFetch("/signup", {
    method: "POST",
    body: JSON.stringify({
      email: payload.email,
      password: payload.password
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
