import { NextResponse } from "next/server";

import { supabaseAuthFetch } from "@/lib/server-auth";

export async function POST(request: Request) {
  const payload = await request.json();
  await supabaseAuthFetch("/recover", {
    method: "POST",
    body: JSON.stringify({ email: payload.email })
  });
  return NextResponse.json({
    status: "submitted",
    message: "If an account can receive recovery email, instructions will be sent."
  });
}
