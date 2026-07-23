import { NextResponse } from "next/server";

import { getValidAccessToken, supabaseAuthFetch } from "@/lib/server-auth";

export async function POST(request: Request) {
  const payload = await request.json();
  const result = NextResponse.json({ status: "password_updated" });
  const token = await getValidAccessToken(result);
  if (!token) {
    return NextResponse.json({ detail: "Reset session is missing or expired." }, { status: 401 });
  }
  const response = await supabaseAuthFetch("/user", {
    method: "PUT",
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify({ password: payload.password })
  });
  const body = await response.json();
  if (!response.ok) {
    return NextResponse.json({ detail: "Password reset failed." }, { status: response.status });
  }
  void body;
  return result;
}
