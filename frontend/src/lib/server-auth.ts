import { cookies } from "next/headers";
import { NextResponse } from "next/server";

const SESSION_COOKIE = process.env.SESSION_COOKIE_NAME ?? "defi_copilot_session";
const REFRESH_COOKIE = `${SESSION_COOKIE}_refresh`;
const EXPIRES_COOKIE = `${SESSION_COOKIE}_expires_at`;
export const ANONYMOUS_COOKIE = process.env.ANONYMOUS_SESSION_COOKIE_NAME ?? "defi_copilot_anon";

export function backendApiBaseUrl(): string {
  return process.env.BACKEND_API_BASE_URL ?? "http://127.0.0.1:8000";
}

export function supabaseConfig() {
  return {
    url: process.env.SUPABASE_URL ?? process.env.NEXT_PUBLIC_SUPABASE_URL ?? "",
    anonKey: process.env.SUPABASE_ANON_KEY ?? process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ?? ""
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

export async function setSupabaseSessionCookies(
  response: NextResponse,
  session: { access_token?: string; refresh_token?: string; expires_in?: number },
) {
  const expiresIn = Math.max(Number(session.expires_in ?? 3600), 60);
  if (session.access_token) {
    response.cookies.set(SESSION_COOKIE, session.access_token, cookieOptions(expiresIn));
  }
  if (session.refresh_token) {
    response.cookies.set(REFRESH_COOKIE, session.refresh_token, cookieOptions(60 * 60 * 24 * 30));
  }
  response.cookies.set(EXPIRES_COOKIE, String(Date.now() + expiresIn * 1000), cookieOptions(expiresIn));
}

export async function clearSessionCookie(response: NextResponse) {
  response.cookies.delete(SESSION_COOKIE);
  response.cookies.delete(REFRESH_COOKIE);
  response.cookies.delete(EXPIRES_COOKIE);
}

export function jsonWithSessionCookies(
  sessionResponse: NextResponse,
  body: unknown,
  status = 200,
): NextResponse {
  const response = NextResponse.json(body, { status });
  for (const cookie of sessionResponse.headers.getSetCookie?.() ?? []) {
    response.headers.append("set-cookie", cookie);
  }
  return response;
}

export async function readSessionToken(): Promise<string> {
  const store = await cookies();
  return store.get(SESSION_COOKIE)?.value ?? "";
}

export async function getValidAccessToken(response: NextResponse): Promise<string> {
  const store = await cookies();
  const accessToken = store.get(SESSION_COOKIE)?.value ?? "";
  const refreshToken = store.get(REFRESH_COOKIE)?.value ?? "";
  const expiresAt = Number(store.get(EXPIRES_COOKIE)?.value ?? 0);
  if (accessToken && expiresAt > Date.now() + 30_000) {
    return accessToken;
  }
  if (!refreshToken) {
    await clearSessionCookie(response);
    return "";
  }
  let refreshResponse: Response;
  let body: Record<string, unknown>;
  try {
    refreshResponse = await supabaseAuthFetch("/token?grant_type=refresh_token", {
      method: "POST",
      body: JSON.stringify({ refresh_token: refreshToken })
    });
    body = await refreshResponse.json();
  } catch {
    await clearSessionCookie(response);
    return "";
  }
  if (!refreshResponse.ok) {
    await clearSessionCookie(response);
    return "";
  }
  await setSupabaseSessionCookies(response, body);
  return typeof body.access_token === "string" ? body.access_token : "";
}

export async function recordMfaAuditEvent(
  accessToken: string,
  action: "mfa.enrollment_started" | "mfa.challenge_verified" | "mfa.factor_unenrolled",
  factorId?: string,
): Promise<boolean> {
  const auditSecret = process.env.BFF_AUDIT_SECRET;
  if (!auditSecret) {
    return false;
  }
  try {
    const response = await fetch(`${backendApiBaseUrl()}/api/auth/mfa/audit`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${accessToken}`,
        "Content-Type": "application/json",
        "X-BFF-Audit-Key": auditSecret,
      },
      body: JSON.stringify({ action, factor_id: factorId }),
      cache: "no-store",
    });
    return response.ok;
  } catch {
    return false;
  }
}

function cookieOptions(maxAge: number) {
  return {
    httpOnly: true,
    secure: process.env.COOKIE_SECURE !== "false",
    sameSite: "lax" as const,
    path: "/",
    maxAge
  };
}
