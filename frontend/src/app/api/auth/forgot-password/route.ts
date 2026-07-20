import { NextResponse } from "next/server";

import { supabaseAuthFetch } from "@/lib/server-auth";

export async function POST(request: Request) {
  const payload = await request.json();
  const callbackUrl = new URL("/api/auth/recovery-callback", request.url);
  callbackUrl.searchParams.set("next", "/reset-password");
  await supabaseAuthFetch("/recover", {
    method: "POST",
    body: JSON.stringify({ email: payload.email, redirect_to: callbackUrl.toString() })
  });
  return NextResponse.json({
    status: "submitted",
    message: "If an account can receive recovery email, instructions will be sent."
  });
}
