# Phase 22 F1-C2 Correction Report

- Review date: 2026-10-22
- Repository: `publiomcko-cloud/defi-thesis-risk-copilot`
- Draft PR: [#43](https://github.com/publiomcko-cloud/defi-thesis-risk-copilot/pull/43)
- Phase status: **ACTIVE — HOLD**
- Profile reviewed: isolated technical-portfolio and restricted personal research; not commercial high-availability SaaS.

## Provenance and reviewer

- F1-C2 authorization: SHA-256 `c2c483796f99f8a941527d3c8013c404a32c332d3105abca6ac12b13435d17b1`.
- F1-R2 rereview: `/home/publio/phase22-f1-r2-independent-rereview-20261022.md`, SHA-256 `c346854433756148f2e8eb38810868b87c39d671fcc26715f5d3995ef9632113`.
- Verified base: `1574d83ab7c0ea0eebef22d0f2d00bc3ce2ed176`.
- R2-reviewed implementation/package: `2e320c5c1d09cf7671a303ef3fb71e2009841351` / `417c44f45742082fa64218ada050be8075829446`.
- Core F1-C2 correction commit: `035204f6328489f853716011657ac57b9a076fc1` (parent `417c44f45742082fa64218ada050be8075829446`).
- Exact tested source head: `15a5497924a94e2015012942065e3cf5cf7d2358`, parent `1f62eec817515348e2b652c24528f7a7b4c22579`, tree `86c2e2353c3f1c64f6505a2cd144ea8fd26ddc62`.
- This report package is based on source head `15a5497`; the package commit is recorded in Git history and PR metadata after packaging.

Reviewer attribution is to this Codex agent session. **Authenticated second-party independence is not demonstrable**: there is no authenticated human reviewer identity or separate principal/session evidence. This report is not independent approval, owner acceptance, or deployment authorization.

## Required statuses

- `F1C2_SOURCE_IDENTITY_STATUS`: **VERIFIED** — corrected branch and base identities are recorded above; PR #43 remains open and draft.
- `F1C2_TOKEN_BUDGET_STATUS`: **FIXED_AND_VERIFIED** — accepted synthesis requires valid usage, independently enforces output and total budgets, and uses the larger of provider-reported total and the input/output component sum. Missing components, invalid values, inconsistent totals, or over-budget usage select deterministic fallback.
- `F1C2_PROVIDER_USAGE_PROVENANCE_STATUS`: **FIXED_AND_VERIFIED_WITH_EXTERNAL_CHARGE_LIMIT** — rejected responses retain observed input/output tokens, reported and effective totals, cost, and response state. Unknown usage is not zero. Post-response enforcement cannot undo tokens or charges already consumed by an external provider. No real provider was activated or called.
- `F1C2_EXECUTION_OWNERSHIP_STATUS`: **FIXED_AND_VERIFIED_FOR_POSTGRESQL** — a nonblocking owner-scoped PostgreSQL transaction advisory lock is acquired on a dedicated connection before reservation and retained through report commit. Status reconciliation, thesis update/delete, and account deletion use the same owner fence. Connection or lock acquisition failure does not proceed unlocked.
- `F1C2_POST_DELETION_EXECUTION_STATUS`: **FIXED_AND_VERIFIED** — the service revalidates owner, thesis, run state, and input checksum at execution and save boundaries. Deletion during a run receives a safe conflict; after completion, deletion scrubs the report and later research is denied. No post-deletion workflow or report resurrection was observed in the deterministic PostgreSQL barrier tests.
- `F1C2_POSTGRES_CONCURRENCY_STATUS`: **PASS_ON_EXACT_TESTED_HEAD** — CI used its explicitly isolated loopback PostgreSQL database. Barrier tests cover reservation/status/deletion handoff, active deletion, same-key concurrency, crash boundaries, completion versus deletion, one workflow/report, and no replay. The local environment skipped the two PostgreSQL-only tests; exact-head CI ran them.
- `F1C2_CITATION_PARITY_STATUS`: **FIXED_AND_VERIFIED** — backend and frontend use one documented fail-closed display policy and shared adversarial fixture corpus (66 cases). It rejects unsafe schemes, credentials, malformed/local/private destinations, ambiguous encodings and disallowed IP/IDN hosts, while allowing approved public HTTPS and repository Markdown references. This is not authorization to fetch URLs or a complete SSRF control for any future fetcher.
- `F1C2_REGRESSION_STATUS`: **PASS_ON_EXACT_TESTED_HEAD** — full CI backend/PostgreSQL, frontend build/typecheck/browser checks, CodeQL, supply-chain/security, Compose, and isolated failure-exercise workflows passed on `15a5497`. Focused local F1 tests passed; PostgreSQL-only tests were skipped locally.
- `F1C2_R3_RESERVED_PATH_STATUS`: **VERIFIED_UNCHANGED** — `docs/deployment.md` is byte-identical to base. R3.15 decision #9 remains pending.
- `F1C2_REMAINING_BLOCKERS`: **NONE_IDENTIFIED_FOR_ISOLATED_DETERMINISTIC_PORTFOLIO_IMPLEMENTATION_WITH_POSTGRESQL** — final F1 rereview remains required before acceptance. Real-provider activation still requires explicit owner decisions on provider/model, data transmission and retention, route promotion/classification, credentials, token budget, and cost ceiling. Hosted deployment remains unverified. SQLite locking is process-local; PostgreSQL is required for the reviewed cross-process ownership guarantee.
- `F1C2_FINAL_VERDICT`: **READY_FOR_F1_FINAL_REREVIEW** — this is not F1 acceptance, `PERSONAL_RESEARCH_READY`, or production readiness.

## Correction findings and bounded behavior

**B1 — token budgets.** Usage fields are range-checked and totals must agree when all three fields are present. A missing reported total can be derived only when both input and output counts are known; incomplete usage is rejected. The persisted provenance keeps the provider-reported total separate from the effective total. Tests cover a too-small or too-large reported total, missing total with over-budget components, independent output overflow, incomplete and negative usage, exact-limit acceptance, and retaining rejected-call usage/cost. Preflight cost checks and provider output caps remain in place. A provider can consume tokens or incur charges before the response is checked.

**B2 — ownership and lifecycle race.** PostgreSQL execution ownership starts before a `running` reservation is committed. The pinned connection holds its transaction-scoped advisory lock across independent application commits; rollback/connection loss releases the lock. Transaction-pooler use relies on the open transaction pinning its backend for the request. Reconciliation that cannot acquire the same owner fence leaves active work untouched. After a crash with a committed reservation, recovery records an uncertain/interrupted result and does not replay provider work. SQLite uses only an in-process lock and is not evidence of cross-process ownership. No Phase 17 worker lease or experimental time floor was added.

**B3 — citation policy.** The shared specification, fixtures, backend checks, frontend checks, report rendering, and Markdown export now follow the same destination policy. URLs remain display metadata; no arbitrary URL fetching was introduced.

## Regression history and preserved decisions

Initial exact-head CI failures were retained and diagnosed. Run `39863990083` exposed an incomplete synthetic report fixture plus a test stub that leaked across tests; the resulting report lookup failure was cascading. Run `39864671835` then found one test assertion expecting report metadata status instead of the API run status. These were test-only fixture/expectation defects, fixed in commits `1f62eec` and `15a5497`; the exact tested head passed. The earlier seven F1-C backend failures and their recorded causes remain in the prior [checksummed F1-C report](phase_22_f1c_correction_report.md); they have not been replaced by or conflated with these later CI failures.

Historical R3 failures **H1–H7 remain open**. All ten R3.15 owner decisions remain **`PENDING_EXPLICIT_OWNER_DECISION`**; no decision was accepted. The CI failure-exercise workflow does not close historical R3 failures.

## Exact-head verification

All runs below completed successfully on source head `15a5497924a94e2015012942065e3cf5cf7d2358`:

- [CI: backend/PostgreSQL, frontend/browser, and Compose](https://github.com/publiomcko-cloud/defi-thesis-risk-copilot/actions/runs/39865301897)
- [Supply chain, dependency/container security, secret scan, and SBOM](https://github.com/publiomcko-cloud/defi-thesis-risk-copilot/actions/runs/39865301902)
- [CodeQL](https://github.com/publiomcko-cloud/defi-thesis-risk-copilot/actions/runs/39865301981)
- [Isolated failure exercises](https://github.com/publiomcko-cloud/defi-thesis-risk-copilot/actions/runs/39865302192)

`docs/deployment.md` has no diff from base and `git diff --check` passed. The full F1-C2 source delta from the R2 package is 23 paths:

```text
backend/app/api/routes_auth.py
backend/app/llm/governance.py
backend/app/llm/provenance.py
backend/app/llm/synthesis.py
backend/app/models/model_governance.py
backend/app/rag/source_urls.py
backend/app/reports/markdown_export.py
backend/app/research_copilot/execution.py
backend/app/research_copilot/service.py
backend/app/schemas/research.py
backend/app/tests/test_citation_url_policy.py
backend/app/tests/test_llm_synthesis.py
backend/app/tests/test_phase22_postgres_research_ownership.py
backend/app/theses/service.py
backend/migrations/versions/20261022_0036_add_reported_provider_token_total.py
docs/citation_url_policy.md
docs/phase_22_f1_implementation.md
frontend/package.json
frontend/scripts/citation-url-policy-check.ts
frontend/src/components/ResearchRunEvidencePanel.tsx
frontend/src/lib/citation-url.ts
frontend/src/lib/types.ts
shared/citation_url_fixtures.json
```

No production system, production data, deployment, real provider, worker, schedule, merge, or time-floor was accessed or activated. Phase 22 remains **ACTIVE — HOLD**.

## Bounded implementation requirements

1. Keep the portfolio integration isolated and use PostgreSQL wherever cross-process execution/lifecycle ownership is required; treat SQLite as a single-process development fallback only.
2. Keep real provider use disabled until the named owner decisions are explicit; never describe post-call budget rejection as retroactive cost prevention.
3. Preserve uncertain crash outcomes without automatic replay or new-key retry; preserve deletion scrubbing and the shared citation display policy.
4. Keep H1–H7 open, all ten R3.15 decisions pending, and `docs/deployment.md` reserved and unchanged.
5. Obtain final F1 rereview before acceptance. Do not merge, deploy, enable workers/schedules, or mark Phase 22 released under this report.

## Portable checksum

Verify from this directory with:

```bash
sha256sum -c phase_22_f1c2_correction_report.md.sha256
```
