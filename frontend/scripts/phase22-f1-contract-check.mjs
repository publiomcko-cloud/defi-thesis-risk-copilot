import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const panel = await readFile(new URL("../src/components/ThesisResearchPanel.tsx", import.meta.url), "utf8");
const evidence = await readFile(new URL("../src/components/ResearchRunEvidencePanel.tsx", import.meta.url), "utf8");
const bff = await readFile(new URL("../src/app/api/backend/[...path]/route.ts", import.meta.url), "utf8");
const types = await readFile(new URL("../src/lib/types.ts", import.meta.url), "utf8");
const citationUrls = await readFile(new URL("../src/lib/citation-url.ts", import.meta.url), "utf8");
const reportViewer = await readFile(new URL("../src/app/reports/[reportId]/report-viewer.tsx", import.meta.url), "utf8");

assert.match(panel, /Bounded synchronous research/);
assert.match(panel, /Research question/);
assert.match(panel, /Idempotency-Key/);
assert.match(panel, /pendingRunKey && pendingRunQuestion === normalizedQuestion/);
assert.match(panel, /Research request is running synchronously/);
assert.match(panel, /The approved model route was used and recorded/);
assert.match(panel, /deterministic synthesis; no approved model route was used/);
assert.match(panel, /Open report/);
assert.match(evidence, /Source observations and freshness/);
assert.match(evidence, /Unresolved evidence/);
assert.match(evidence, /Bounded tool trace/);
assert.match(evidence, /Provider calls observed/);
assert.match(evidence, /research\.provider_call_state/);
assert.match(bff, /AbortSignal\.timeout\(30_000\)/);
assert.match(bff, /export const maxDuration = 35/);
assert.match(bff, /exceeded the BFF time limit/);
assert.match(types, /export type ResearchRunMetadata/);
assert.match(types, /export type ResearchRunSummary/);
assert.match(types, /"interrupted" \| "uncertain"/);
assert.match(panel, /The browser stopped waiting; server execution may have continued/);
assert.match(panel, /do not retry with a new key/i);
assert.match(reportViewer, /Answer to the research question/);
assert.match(citationUrls, /url\.protocol !== "https:"/);
assert.match(citationUrls, /url\.username \|\| url\.password/);

console.log("Phase 22 F1 research workflow UI contract check passed.");
