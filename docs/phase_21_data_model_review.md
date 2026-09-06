# Phase 21 Data-Model Review

Status: **21A and 21B implemented; 21C is next.**

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
