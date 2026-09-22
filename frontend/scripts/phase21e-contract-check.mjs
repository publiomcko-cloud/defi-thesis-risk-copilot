import { readFile } from "node:fs/promises";

const [page, api, bff] = await Promise.all([
  readFile(new URL("../src/app/admin/training-governance/page.tsx", import.meta.url), "utf8"),
  readFile(new URL("../src/lib/api.ts", import.meta.url), "utf8"),
  readFile(new URL("../src/app/api/backend/[...path]/route.ts", import.meta.url), "utf8")
]);

for (const required of ["fetchTrainingGovernance", "sealTrainingManifest", "submitLocalTrainingRun", "Queue Local Evidence"]) {
  if (!page.includes(required) && !api.includes(required)) {
    throw new Error(`Training-governance UI is missing ${required}.`);
  }
}
if (!api.includes("/api/admin/training-governance")) {
  throw new Error("Training-governance API calls must use the bounded administrator route.");
}
if (!bff.includes('"/api/admin/"')) {
  throw new Error("Training-governance requests must remain behind the bounded administrator BFF namespace.");
}
for (const forbidden of ["textarea", "localStorage", "sessionStorage", "indexeddb", "cookie", "credential", "api key", "shell command", "docker image", "vast.ai"]) {
  if (page.toLowerCase().includes(forbidden)) {
    throw new Error(`Training-governance UI must not expose ${forbidden}.`);
  }
}

console.log("Phase 21E training-governance UI contract check passed.");
