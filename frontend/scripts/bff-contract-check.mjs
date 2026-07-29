import { readFile } from "node:fs/promises";

const route = await readFile(new URL("../src/app/api/backend/[...path]/route.ts", import.meta.url), "utf8");

if (route.includes('ALLOWED_PREFIXES = ["/"') || route.includes('"/", "/health"')) {
  throw new Error("BFF route allowlist must not include a catch-all '/' prefix.");
}

if (route.includes('request.headers.get("cookie")') || route.includes("headers.set(\"cookie\", incomingCookie)")) {
  throw new Error("BFF route must not forward the raw browser Cookie header.");
}

if (!route.includes("ANONYMOUS_COOKIE")) {
  throw new Error("BFF route must intentionally forward only the anonymous backend cookie.");
}

if (!route.includes('path.startsWith("/internal/")')) {
  throw new Error("BFF route must explicitly refuse internal worker protocol paths.");
}

if (!route.includes('headers.set("x-correlation-id", correlationId)') || !route.includes('"x-correlation-id"')) {
  throw new Error("BFF route must normalize and forward a correlation ID without forwarding arbitrary headers.");
}

if (!route.includes('x-vercel-forwarded-for') || !route.includes('process.env.VERCEL !== "1"') || !route.includes('isIP(candidate)') || !route.includes('"retry-after"')) {
  throw new Error("BFF route must forward only normalized provider client IPs and safe rate-limit metadata.");
}
if (route.includes('?? request.headers.get("x-forwarded-for")')) {
  throw new Error("BFF route must not fall back to browser-supplied X-Forwarded-For.");
}
if (!route.includes('readBodyWithinLimit(request, bffBodyLimit(targetPath))')) {
  throw new Error("BFF route must enforce a measured body limit before forwarding requests.");
}

if (!route.includes("hasTrustedOrigin(request)") || !route.includes("Browser origin is not allowed.")) {
  throw new Error("BFF route must reject cross-origin browser mutations before forwarding cookies or tokens.");
}

if (!route.includes('redirect: "manual"') || !route.includes("Backend redirect rejected.")) {
  throw new Error("BFF route must reject backend redirects to prevent redirect-based SSRF.");
}

console.log("BFF contract check passed.");
