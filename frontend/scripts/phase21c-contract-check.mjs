import { readFile } from "node:fs/promises";

const [viewer, feedback, api, bff] = await Promise.all([
  readFile(new URL("../src/app/reports/[reportId]/report-viewer.tsx", import.meta.url), "utf8"),
  readFile(new URL("../src/components/ReportFeedbackForm.tsx", import.meta.url), "utf8"),
  readFile(new URL("../src/lib/api.ts", import.meta.url), "utf8"),
  readFile(new URL("../src/app/api/backend/[...path]/route.ts", import.meta.url), "utf8")
]);

for (const category of ["helpful", "incorrect", "missing_source", "bad_citation", "unclear", "entity_error", "unsafe"]) {
  if (!feedback.includes(`value: \"${category}\"`)) throw new Error(`Missing feedback category ${category}`);
}
if (!viewer.includes("<ReportFeedbackForm") || !api.includes("submitModelFeedback")) {
  throw new Error("Persisted reports must render the bounded feedback form.");
}
for (const forbidden of ["localStorage", "sessionStorage", "IndexedDB", "console.log", "analytics"]) {
  if (feedback.includes(forbidden)) throw new Error(`Feedback UI must not persist or log comments: ${forbidden}`);
}
if (!bff.includes("isModelFeedbackRoute") || bff.includes('"/api/model-feedback/",')) {
  throw new Error("Feedback BFF routes must remain exact and method-bound.");
}

console.log("Phase 21C feedback UI contract check passed.");
