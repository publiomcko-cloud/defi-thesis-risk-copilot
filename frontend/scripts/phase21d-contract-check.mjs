import { readFile } from "node:fs/promises";

const [thesisPanel, reportPanel, bff] = await Promise.all([
  readFile(new URL("../src/components/ThesisResearchPanel.tsx", import.meta.url), "utf8"),
  readFile(new URL("../src/components/ReportResearchPanel.tsx", import.meta.url), "utf8"),
  readFile(new URL("../src/app/api/backend/[...path]/route.ts", import.meta.url), "utf8")
]);

for (const route of ["/history", "/assumptions", "/catalysts", "/monitoring-questions"]) {
  if (!thesisPanel.includes(route)) throw new Error(`Thesis research UI is missing ${route}.`);
}
for (const route of ["/reports/compare", "/source-staleness"]) {
  if (!reportPanel.includes(route)) throw new Error(`Report research UI is missing ${route}.`);
}
if (!bff.includes('"/api/research/scenarios/compare"')) {
  throw new Error("The bounded scenario-comparison endpoint must be explicitly allowlisted.");
}
for (const forbidden of ["localStorage", "sessionStorage", "IndexedDB", "console.log", "analytics", "provider", "wallet", "position size"]) {
  if (thesisPanel.toLowerCase().includes(forbidden) || reportPanel.toLowerCase().includes(forbidden)) {
    throw new Error(`Research intelligence UI must not persist, log, or expose forbidden authority: ${forbidden}`);
  }
}

console.log("Phase 21D research-intelligence UI contract check passed.");
