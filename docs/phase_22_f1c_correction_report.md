# Phase 22 F1-C Correction Review

- Review date: 2026-10-22
- Repository / PR: `publiomcko-cloud/defi-thesis-risk-copilot`, draft PR #43
- Reviewed implementation commit: `2e320c5c1d09cf7671a303ef3fb71e2009841351`
- Reviewed tree: `e1e06f9785420b36096303eed34300d9b341a0ca`
- Base: `1574d83ab7c0ea0eebef22d0f2d00bc3ce2ed176`
- Phase status: ACTIVE — HOLD

## Provenance and reviewer

The F1-C owner authorization attachment was verified at SHA-256
`46fc20d2caf2870f1b0915c84f3e5d2ca24af3a82575bf6b16a083c909e849e8`. The
complete F1 independent source review was read and verified at SHA-256
`adf2f012bc3eb6ccb003699fe7ff54e19d9108cd100f1b1631a37409688b8882`. It
reviews baseline head `68f54885e76d18b7414c95b08dcd929e5e3ef894`; PR #43 still
targets the verified base above. The correction branch contains the reviewed
implementation tree shown above. `docs/deployment.md` has no content difference
from the verified base.

Reviewer attribution is to this Codex agent session. **Authenticated second-party
independence is not demonstrable**: no authenticated human reviewer identity or
separate principal/session evidence is available. This report is not independent
approval or F1 acceptance.

## Required statuses

- `F1C_SOURCE_PROVENANCE_STATUS`: **VERIFIED** — authorization, source-review hash, base, PR, implementation commit, and tree recorded above.
- `F1C_QUESTION_ANSWER_STATUS`: **FIXED_AND_VERIFIED** — report contains bounded question-specific source excerpts and citations; unmatched terms and insufficient evidence are explicit; lexical matches always remain `weak` and never claim semantic entailment. At most one follow-up retrieval is triggered by unmatched question terms or missing protocol evidence, not document count or the semantic limitation alone.
- `F1C_PROMPT_BOUNDARY_STATUS`: **FIXED_AND_VERIFIED** — code-owned policy is sent in the provider system field; question and strategy are labeled untrusted task data; retrieved evidence and metadata remain untrusted; saved assumptions stay outside synthesis. Prompt/safety versions are v4/v3; v3 remains unchanged and its promotion does not authorize v4.
- `F1C_PROVIDER_USAGE_ACCOUNTING_STATUS`: **FIXED_AND_VERIFIED** — distinguishes pre-transmission rejection, uncertain call outcome, received-but-rejected response, and accepted output; available usage/cost survives fallback; unknown is not reported as zero. Post-call rejection does not reverse provider charges.
- `F1C_DATA_LIFECYCLE_STATUS`: **FIXED_AND_VERIFIED_WITH_EVENT_BASED_RETENTION** — account export includes F1 runs/reports; thesis/account deletion scrubs payloads, reports, feedback, and model provenance and denies access to disposed reports. There is no automatic TTL: data is retained until owner deletion. Provider-side retention remains an owner decision before any real provider call.
- `F1C_INTERRUPTED_RUN_RECOVERY_STATUS`: **FIXED_AND_VERIFIED_WITH_BOUNDS** — PostgreSQL transaction advisory lock prevents a status read from terminating an active request; an unlocked run is reconciled against its committed report or marked interrupted with uncertain outcome/usage. SQLite cannot prove cross-process ownership and reports uncertainty without replay. No worker or automatic replay is added.
- `F1C_R3_RESERVED_PATH_STATUS`: **FIXED_AND_VERIFIED** — `docs/deployment.md` is byte-identical to base; R3.15 decision #9 remains pending.
- `F1C_TIMEOUT_RECONCILIATION_STATUS`: **FIXED_AND_VERIFIED; DEPLOYMENT_UNVERIFIED** — 25-second backend bound, 30-second BFF timeout, 35-second route maximum; client timeout is not cancellation, the same idempotency key is reconciled after failure/refresh, and statuses distinguish running, completed, failed, interrupted, and uncertain. Hosted Vercel behavior was not verified.
- `F1C_CITATION_URL_SAFETY_STATUS`: **FIXED_AND_VERIFIED** — display paths accept public HTTPS without userinfo and validated `docs/` or `knowledge_base/` Markdown references; unsafe schemes, malformed/credential-bearing links, and local/private literal IPs are rejected or neutralized. Curated local references are canonicalized through the same policy. F1 citation URLs are not fetched server-side; any future fetcher needs separate DNS/connection-time SSRF controls.
- `F1C_REGRESSION_STATUS`: **PASS_ON_REVIEWED_TREE** — local full backend suite, targeted F1/retrieval/lifecycle tests, Python compile and dependency checks, frontend TypeScript/build, F1 contract, and BFF contract checks passed. Exact-head GitHub checks are linked below.
- `F1C_REMAINING_BLOCKERS`: **NONE_FOR_ISOLATED_DETERMINISTIC_PORTFOLIO_IMPLEMENTATION**. Independent F1 rereview remains required before acceptance. Real-provider activation still requires owner decisions on provider/model, private-data transmission and retention, route classification/promotion, credentials, token budget, and cost ceiling. Deployment remains unverified.
- `F1C_FINAL_VERDICT`: **READY_FOR_F1_INDEPENDENT_REREVIEW**.

## Finding resolution matrix

| Finding | Resolution | Evidence / bound |
|---|---|---|
| C1 — question answer and evidence gap | `FIXED_AND_VERIFIED` | Extractive source sentences only; citations, unmatched terms, lexical conflicts, insufficient outcome, and semantic limitation are visible. |
| C2 — prompt trust boundary | `FIXED_AND_VERIFIED` | Actual provider system field; untrusted task/evidence data; assumptions excluded; new prompt version. |
| C3 — rejected-call accounting | `FIXED_AND_VERIFIED` | Fake-provider tests retain observed token/cost data on rejected output and represent uncertain transport usage. No real provider call. |
| C4 — lifecycle and export | `FIXED_AND_VERIFIED` | Export and thesis/account disposal tests cover run/report payload, access denial, feedback, and model provenance. Retention is event-based with no automatic TTL. |
| C5 — interrupted synchronous run | `FIXED_AND_VERIFIED` | SQLite fail-closed behavior and PostgreSQL advisory-lock integration test; no automatic replay, new key, worker, or lease. |
| C6 — reserved R3.15 path | `FIXED_AND_VERIFIED` | Deployment doc restored to base; decision #9 not accepted. |
| C7 — timeout and reconciliation | `FIXED_AND_VERIFIED` | Browser/BFF/backend bounds and same-key status reconciliation; hosted limits remain `DEPLOYMENT_UNVERIFIED`. |
| C8 — citation URLs | `FIXED_AND_VERIFIED` | URL adversarial tests; same allowlist across retrieval, answer/report schemas, export, and frontend links. No F1 server-side URL fetch. |

## Initial failures preserved and resolved

The first full local backend run had seven failures. Five legacy retrieval/public-corpus failures showed that strict citation validation rejected absolute loader paths and curated paths relative to the corpus root; loaders and the trusted curated retriever now emit validated repository-relative references. One C1 test found missing polarity token sets; those are now derived from the bounded polarity groups. One lifecycle test read an expired ORM object after its session closed; it now captures the primary key while attached. Targeted tests for these cases pass.

A subsequent C1 regression caught singular/plural mismatch (`increase`/`increases`) causing unnecessary follow-up; bounded normalization and a test now cover it. The first frontend contract run had a case-sensitive assertion mismatch, corrected without changing UI behavior. The first TypeScript check raced with `next build` regenerating `.next/types`; the sequential rerun passed. The first Gitleaks run identified two synthetic idempotency fixtures in the correction commit; the correction commits were consolidated with low-entropy `test-key` fixtures. The final Gitleaks check passed, with no ignore rule added.

## Exact-source CI evidence

These GitHub Actions runs passed on implementation commit
`2e320c5c1d09cf7671a303ef3fb71e2009841351`:

- [CI — backend and PostgreSQL, frontend build/typecheck/browser E2E, Compose](https://github.com/publiomcko-cloud/defi-thesis-risk-copilot/actions/runs/39842704028)
- [Supply Chain Security — secret scan, dependency review, SBOM and container scans](https://github.com/publiomcko-cloud/defi-thesis-risk-copilot/actions/runs/39842703993)
- [CodeQL](https://github.com/publiomcko-cloud/defi-thesis-risk-copilot/actions/runs/39842703995)
- [Isolated failure exercises](https://github.com/publiomcko-cloud/defi-thesis-risk-copilot/actions/runs/39842703948)

The isolated failure-exercise job is a CI result only; it does not close historical
R3 failures. H1–H7 remain open, and all ten R3.15 owner decisions remain pending.
No pending decision was accepted. No provider was activated; no production data,
deployment, merge, worker, schedule, or time-floor was accessed or enabled.

## Bounded implementation requirements

1. Keep the candidate isolated to the authenticated private-thesis route; keep real providers, workers, schedules, and the experimental time floor disabled.
2. Use PostgreSQL for cross-process execution ownership. Treat SQLite stale runs as uncertain; do not replay unknown runs under a new idempotency key.
3. Keep every lexical answer visibly weak and source-linked. Do not present overlap or polarity heuristics as semantic entailment.
4. Preserve `DEPLOYMENT_UNVERIFIED`. Before real-provider use, obtain the listed owner decisions and perform synthetic-first provider acceptance.
5. Require independent F1 rereview before F1 acceptance. Phase 22 remains ACTIVE — HOLD; this report does not claim `PERSONAL_RESEARCH_READY` or production readiness.

## Portable checksum

Verify the companion file with:

```sh
sha256sum -c phase_22_f1c_correction_report.md.sha256
```
