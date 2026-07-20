import { NextResponse } from "next/server";

import { setSessionCookie, supabaseAuthFetch } from "@/lib/server-auth";

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
  const result = NextResponse.json({ status: "authenticated" });
  await setSessionCookie(result, body.access_token);
  return result;
}
