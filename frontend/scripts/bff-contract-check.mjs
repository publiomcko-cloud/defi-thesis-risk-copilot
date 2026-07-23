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

console.log("BFF contract check passed.");
