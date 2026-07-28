import { NextRequest } from "next/server";

export function hasTrustedOrigin(request: NextRequest): boolean {
  const origin = request.headers.get("origin");
  if (!origin) {
    return true;
  }
  try {
    const originUrl = new URL(origin);
    const configuredOrigins = (process.env.BFF_ALLOWED_ORIGINS ?? "")
      .split(",")
      .map((value) => value.trim().replace(/\/$/, ""))
      .filter(Boolean);
    if (configuredOrigins.length > 0) {
      return configuredOrigins.includes(originUrl.origin);
    }
    const forwardedHost = firstHeaderValue(request.headers.get("x-forwarded-host"));
    const requestHost = forwardedHost || request.headers.get("host") || request.nextUrl.host;
    if (originUrl.host !== requestHost) {
      return false;
    }
    const forwardedProtocol = firstHeaderValue(request.headers.get("x-forwarded-proto"));
    return !forwardedProtocol || originUrl.protocol === `${forwardedProtocol}:`;
  } catch {
    return false;
  }
}

function firstHeaderValue(value: string | null): string {
  return value?.split(",", 1)[0]?.trim() ?? "";
}
