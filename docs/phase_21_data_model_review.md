# Phase 21 Data-Model Review

Status: **21A–21D implemented locally; 21E is next.**

## 21B Migration

`20260906_0031_add_model_evaluation_routing.py` follows
`20260904_0030` and is the only 21B revision. It is reversible:

```text
0030 -> 0031 -> 0030 -> 0031
```

It leaves all Phase 20 tables and the exact `free-v1` limits unchanged. It
does not fill reserved/deferred revision `0027` and does not alter 0030.

## Durable Governance State

| Table | Role | Sensitive-content boundary |
| --- | --- | --- |
| `model_evaluation_datasets` | Immutable checked-in corpus identity/version/checksum/count | No cases, prompts, chunks, or outputs |
| `model_evaluation_runs` | Candidate/baseline/prompt/policy/environment aggregate evidence | Bounded IDs, metrics, timestamps, reason codes only |
| `model_evaluation_case_results` | Immutable hashed case result metrics | Case ID/checksum and bounded result/usage fields only |
| `model_route_versions` | Immutable promoted route history | Registry/prompt/evaluation IDs only |
| `model_route_assignments` | One mutable task/version/environment authority pointer | No credentials or arbitrary metadata |
| `model_route_transitions` | Immutable promotion/rollback audit history | Bounded actor/action/reason identifiers only |

`model_run_provenance` gains nullable `route_version_id` and
`evaluation_run_id` foreign keys. These are safe reference IDs, not evaluation
content. Existing account/report lifecycle removal remains unchanged; route and
evaluation governance evidence is not tenant content because 21B forbids tenant
content in its datasets and persisted evaluation data.

Async execution snapshots intentionally add no table or migration. At the
server-owned Phase 17 start transition, a bounded, credential-free route
snapshot is written once into the existing durable job `_server_context`:
task/version, environment, scope, route/evaluation/model/prompt references and
checksum, plus provider identity fields only. The authenticated start response
returns that context to the worker. Retry/recovery never replaces it. Provider
credentials, raw prompts, output text, and browser-supplied routing data are
not part of the snapshot.

## Authority And Rollback

An active assignment is valid only when it resolves a completed,
promotion-eligible evaluation, exact current prompt, non-retired evaluated
registry model, and exact server-configured adapter identity. The global
`LLM_SYNTHESIS_ENABLED=false` kill switch overrides all routes. Empty/invalid
assignment, unavailable/mismatched adapter, or unsuitable private/organization
privacy produces deterministic fallback.

Promoting a passing evaluation takes a PostgreSQL row lock on the assignment;
passing never auto-promotes. Rollback takes the same lock and restores only the
route explicitly recorded as the previous known-good route, otherwise it clears
the pointer to the deterministic baseline. History and evaluation evidence are
never deleted by rollback.

Promotion also verifies the completed run against the current code-owned
policy version/checksum, checked-in dataset identity/version/checksum, and
current exact prompt linkage. This makes older or altered evidence ineligible
without mutating it. Assignment changes are prospective: a valid historical
execution snapshot is independently verifiable after a later promotion or
rollback, while missing/corrupt/mismatched snapshot evidence falls back to
deterministic wording with bounded provenance.

## 21C Migration And Quality/Feedback State

`20260907_0032_add_model_quality_feedback.py` follows `20260906_0031` and is
the only 21C revision. Its reversible evidence cycle is:

```text
0031 -> 0032 -> 0031 -> 0032
```

It leaves the Phase 20F `free-v1` catalog and all 21A/21B state intact; the
intentional `0027` gap remains absent. Downgrade removes only the 21C tables,
foreign key, columns, indexes, and check constraints.

| Table/state | Role | Sensitive-content boundary |
| --- | --- | --- |
| `model_run_quality_evidence` | One immutable quality-policy result linked to a model run | Policy/checksum, booleans, bounded counts/reason only; no raw output/prompt/chunks |
| `model_evaluation_runs` quality columns | Aggregate 21C hard-gate evidence | Bounded counters only |
| `model_evaluation_case_results` quality columns | Immutable bounded per-case quality observations | Case checksum/ID and bounded metrics only |
| `model_feedback` | User-owned report-context feedback and explicit review state | Closed category, <=1000-char comment, safe references; no attachments, metadata blobs, report body, prompt, retrieval text, or credentials |

Feedback derives owner and organization from the accessible durable report.
Users cannot select tenant scope; platform administration is review authority,
not a private-content bypass. Account deletion removes owned feedback, report
deletion cascades it, expiry makes it inaccessible, and organization deletion
clears its context reference. Approval moves `submitted` through explicit
review to `approved_for_dataset` or `rejected`, and stores only a safe
future-review reference. It does not mutate a versioned dataset, model route,
prompt, registry, or training state.

## 21D Research-Intelligence State

`20260910_0033_add_research_intelligence.py` follows `20260907_0032` and is
the only 21D revision. Its reversible evidence cycle is:

```text
0032 -> 0033 -> 0032 -> 0033
```

| Table | Role | Sensitive-content boundary |
| --- | --- | --- |
| `thesis_revisions` | Immutable thesis/status snapshots with a per-thesis monotonic unique revision and exact current-assumption record/version references | Existing thesis text and legacy assumptions only; no provider payload or analytics copy |
| `thesis_assumptions` | Append-only statement/state/evidence versions | Report-backed references retain durable lineage IDs/checksums; free text is explicitly `unverified_external` |
| `thesis_assumption_heads` | Lockable pointer to one current immutable assumption version | IDs and bounded revision number only; PostgreSQL serializes supersession |
| `thesis_catalysts` | Bounded research event/date-window/uncertainty state with optimistic revision | User-recorded text only; no price target, trade signal, notification, or schedule |
| `research_report_comparisons` | Same-scope deterministic report-diff provenance | IDs, input/lineage checksums, and compact field classifications; no complete report body duplication |

`saved_theses` remains the compatibility and CRUD authority. A legacy baseline
is created locally and idempotently under the thesis lock before a first
mutation, preserving original content exactly. Later snapshots reference the
immutable assumption record and revision current at snapshot time, not only its
logical assumption ID. Report-backed evidence must exactly match the destination
thesis private-owner or organization scope. Thesis soft deletion removes derived 21D rows; account and
organization deletion dispose owned/scoped research rows. Report comparison and
staleness reads reauthorize both underlying reports, so report expiry/deletion
or membership loss cannot turn derived state into a private-content backdoor.
