import { readFile } from "node:fs/promises";

const config = await readFile(new URL("../next.config.js", import.meta.url), "utf8");
const bffRoute = await readFile(new URL("../src/app/api/backend/[...path]/route.ts", import.meta.url), "utf8");
const requestSecurity = await readFile(new URL("../src/lib/request-security.ts", import.meta.url), "utf8");
const serverAuth = await readFile(new URL("../src/lib/server-auth.ts", import.meta.url), "utf8");

for (const header of [
  "Content-Security-Policy-Report-Only",
  "X-Content-Type-Options",
  "X-Frame-Options",
  "Referrer-Policy",
  "Permissions-Policy",
  "Strict-Transport-Security"
]) {
  if (!config.includes(header)) {
    throw new Error(`Missing Phase 19C browser security header: ${header}`);
  }
}
if (!config.includes("SECURITY_CSP_MODE") || !config.includes("SECURITY_HSTS_ENABLED")) {
  throw new Error("CSP and HSTS must remain explicit deployment controls.");
}
if (!requestSecurity.includes("BFF_ALLOWED_ORIGINS") || !bffRoute.includes("hasTrustedOrigin(request)")) {
  throw new Error("Mutating BFF calls must use an exact configured origin allowlist.");
}
if (!bffRoute.includes("target.origin !== backendOrigin") || !bffRoute.includes("Backend redirect rejected.")) {
  throw new Error("BFF backend target and redirect protections are required.");
}
if (!serverAuth.includes("BACKEND_API_BASE_URL must be an origin")) {
  throw new Error("BFF backend origin must reject credentials and paths.");
}

console.log("Frontend security header contract check passed.");
