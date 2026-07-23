export type MfaFactor = {
  id: string;
  status: "verified" | "unverified";
  friendly_name: string;
  factor_type: string;
  created_at: string | null;
  updated_at: string | null;
  last_challenged_at: string | null;
};

export type MfaState = {
  current_level: "aal1" | "aal2";
  next_level: "aal1" | "aal2";
  factors: MfaFactor[];
};

export type MfaEnrollment = {
  factor_id: string;
  friendly_name: string;
  qr_code: string;
  secret: string;
};

export type MfaProviderResult<T> =
  | { ok: true; status: number; data: T }
  | { ok: false; status: number };

export type SupabaseAuthFetcher = (path: string, init?: RequestInit) => Promise<Response>;

const FACTOR_ID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const TOTP_CODE_PATTERN = /^\d{6,8}$/;
const MAX_QR_CODE_LENGTH = 100_000;
const MAX_SECRET_LENGTH = 256;

export async function loadMfaState(
  token: string,
  authFetch: SupabaseAuthFetcher,
): Promise<MfaProviderResult<MfaState>> {
  const response = await safeAuthFetch(authFetch, "/user", authorizedRequest(token, { method: "GET" }));
  const body = await responseJson(response);
  if (!response.ok) {
    return providerFailure(response.status);
  }

  const rawFactors: unknown[] = Array.isArray(body?.factors) ? body.factors : [];
  const factors = rawFactors.length
    ? rawFactors.map((factor: unknown) => sanitizeFactor(factor)).filter((factor): factor is MfaFactor => factor !== null)
    : [];
  const currentLevel = assuranceLevel(token);
  const nextLevel = factors.some((factor) => factor.status === "verified") ? "aal2" : "aal1";
  return {
    ok: true,
    status: response.status,
    data: { current_level: currentLevel, next_level: nextLevel, factors }
  };
}

export async function enrollTotpFactor(
  token: string,
  friendlyName: string,
  authFetch: SupabaseAuthFetcher,
): Promise<MfaProviderResult<MfaEnrollment>> {
  const normalizedName = friendlyName.trim();
  if (!normalizedName || normalizedName.length > 64 || /[\u0000-\u001f\u007f]/.test(normalizedName)) {
    return { ok: false, status: 400 };
  }
  const response = await safeAuthFetch(authFetch, "/factors", authorizedRequest(token, {
    method: "POST",
    body: JSON.stringify({ factor_type: "totp", friendly_name: normalizedName })
  }));
  const body = await responseJson(response);
  if (!response.ok) {
    return providerFailure(response.status);
  }

  const factorId = typeof body?.id === "string" ? body.id : "";
  const qrCode = normalizeQrCode(body?.totp?.qr_code);
  const secret = sanitizeSecret(body?.totp?.secret);
  if (!isFactorId(factorId) || !qrCode || !secret) {
    return { ok: false, status: 502 };
  }
  return {
    ok: true,
    status: response.status,
    data: {
      factor_id: factorId,
      friendly_name: typeof body?.friendly_name === "string" ? body.friendly_name : normalizedName,
      qr_code: qrCode,
      secret
    }
  };
}

export async function challengeAndVerifyTotp(
  token: string,
  factorId: string,
  code: string,
  authFetch: SupabaseAuthFetcher,
): Promise<MfaProviderResult<Record<string, unknown>>> {
  if (!isFactorId(factorId) || !TOTP_CODE_PATTERN.test(code)) {
    return { ok: false, status: 400 };
  }
  const challengeResponse = await safeAuthFetch(
    authFetch,
    `/factors/${encodeURIComponent(factorId)}/challenge`,
    authorizedRequest(token, { method: "POST", body: "{}" }),
  );
  const challengeBody = await responseJson(challengeResponse);
  if (!challengeResponse.ok) {
    return providerFailure(challengeResponse.status);
  }
  const challengeId = typeof challengeBody?.id === "string" ? challengeBody.id : "";
  if (!isFactorId(challengeId)) {
    return { ok: false, status: 502 };
  }

  const verifyResponse = await safeAuthFetch(
    authFetch,
    `/factors/${encodeURIComponent(factorId)}/verify`,
    authorizedRequest(token, {
      method: "POST",
      body: JSON.stringify({ challenge_id: challengeId, code })
    }),
  );
  const verifyBody = await responseJson(verifyResponse);
  if (!verifyResponse.ok) {
    return providerFailure(verifyResponse.status);
  }
  if (typeof verifyBody?.access_token !== "string" || typeof verifyBody?.refresh_token !== "string") {
    return { ok: false, status: 502 };
  }
  return { ok: true, status: verifyResponse.status, data: verifyBody };
}

export async function unenrollMfaFactor(
  token: string,
  factorId: string,
  authFetch: SupabaseAuthFetcher,
): Promise<MfaProviderResult<Record<string, unknown>>> {
  if (!isFactorId(factorId)) {
    return { ok: false, status: 400 };
  }
  const response = await safeAuthFetch(
    authFetch,
    `/factors/${encodeURIComponent(factorId)}`,
    authorizedRequest(token, { method: "DELETE" }),
  );
  const body = await responseJson(response);
  if (!response.ok) {
    return providerFailure(response.status);
  }
  return { ok: true, status: response.status, data: body };
}

function authorizedRequest(token: string, init: RequestInit): RequestInit {
  return {
    ...init,
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
      ...(init.headers ?? {})
    },
    cache: "no-store"
  };
}

function assuranceLevel(token: string): "aal1" | "aal2" {
  try {
    const payload = token.split(".")[1];
    if (!payload) {
      return "aal1";
    }
    const decoded = JSON.parse(Buffer.from(payload, "base64url").toString("utf8"));
    return decoded?.aal === "aal2" ? "aal2" : "aal1";
  } catch {
    return "aal1";
  }
}

function sanitizeFactor(value: unknown): MfaFactor | null {
  if (!value || typeof value !== "object") {
    return null;
  }
  const factor = value as Record<string, unknown>;
  if (!isFactorId(factor.id) || (factor.status !== "verified" && factor.status !== "unverified")) {
    return null;
  }
  return {
    id: factor.id,
    status: factor.status,
    friendly_name: typeof factor.friendly_name === "string" ? factor.friendly_name.slice(0, 64) : "Authenticator app",
    factor_type: typeof factor.factor_type === "string" ? factor.factor_type : "unknown",
    created_at: safeDateString(factor.created_at),
    updated_at: safeDateString(factor.updated_at),
    last_challenged_at: safeDateString(factor.last_challenged_at)
  };
}

function normalizeQrCode(value: unknown): string {
  if (typeof value !== "string" || value.length > MAX_QR_CODE_LENGTH) {
    return "";
  }
  if (value.startsWith("data:image/svg+xml")) {
    return value;
  }
  const svgStart = value.indexOf("<svg");
  if (svgStart === -1) {
    return "";
  }
  return `data:image/svg+xml;charset=utf-8,${encodeURIComponent(value.slice(svgStart))}`;
}

function sanitizeSecret(value: unknown): string {
  if (typeof value !== "string" || !value || value.length > MAX_SECRET_LENGTH || /\s|[\u0000-\u001f\u007f]/.test(value)) {
    return "";
  }
  return value;
}

function safeDateString(value: unknown): string | null {
  return typeof value === "string" && value.length <= 64 ? value : null;
}

function isFactorId(value: unknown): value is string {
  return typeof value === "string" && FACTOR_ID_PATTERN.test(value);
}

async function responseJson(response: Response): Promise<any> {
  try {
    return await response.json();
  } catch {
    return {};
  }
}

async function safeAuthFetch(
  authFetch: SupabaseAuthFetcher,
  path: string,
  init: RequestInit,
): Promise<Response> {
  try {
    return await authFetch(path, init);
  } catch {
    return new Response(null, { status: 502 });
  }
}

function providerFailure(status: number): MfaProviderResult<never> {
  if ([400, 401, 403, 404, 409, 422, 429, 503].includes(status)) {
    return { ok: false, status };
  }
  return { ok: false, status: 502 };
}
