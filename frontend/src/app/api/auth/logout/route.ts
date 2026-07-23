import { NextResponse } from "next/server";

import { clearSessionCookie } from "@/lib/server-auth";

export async function POST() {
  const response = NextResponse.json({ status: "logged_out" });
  await clearSessionCookie(response);
  return response;
}
