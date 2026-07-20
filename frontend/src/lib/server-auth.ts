import { cookies } from "next/headers";
import { NextResponse } from "next/server";

const SESSION_COOKIE = process.env.SESSION_COOKIE_NAME ?? "defi_copilot_session";

export function supabaseConfig() {
  return {
    url: process.env.NEXT_PUBLIC_SUPABASE_URL ?? "",
    anonKey: process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ?? ""
  };
}

export async function supabaseAuthFetch(path: string, init: RequestInit = {}) {
  const config = supabaseConfig();
  if (!config.url || !config.anonKey) {
    return {
      ok: false,
      status: 503,
      json: async () => ({ error_description: "Supabase Auth is not configured." })
    } as Response;
  }
  return fetch(`${config.url}/auth/v1${path}`, {
    ...init,
    headers: {
      apikey: config.anonKey,
      "Content-Type": "application/json",
      ...(init.headers ?? {})
    },
    cache: "no-store"
  });
}

export async function setSessionCookie(response: NextResponse, accessToken?: string) {
  if (!accessToken) {
    return;
  }
  response.cookies.set(SESSION_COOKIE, accessToken, {
    httpOnly: true,
    secure: process.env.COOKIE_SECURE !== "false",
    sameSite: "lax",
    path: "/",
    maxAge: 60 * 60
  });
}

export async function clearSessionCookie(response: NextResponse) {
  response.cookies.delete(SESSION_COOKIE);
}

export async function readSessionToken(): Promise<string> {
  const store = await cookies();
  return store.get(SESSION_COOKIE)?.value ?? "";
}
