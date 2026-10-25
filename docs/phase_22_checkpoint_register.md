# Phase 22 — F1-DOC-01 Recoverable Checkpoint Register

**Snapshot date:** 2026-10-25 (America/Sao_Paulo)  
**Checkpoint class:** documentation-only, source-anchored status and evidence inventory  
**Disposition:** **DOCUMENTED — NOT OWNER RELEASE ACCEPTANCE**  
**Phase state:** **ACTIVE — HOLD**  
**Authoritative production code:** GitHub `main` only. Unmerged branches are candidates, not shipped features.  
**Scope:** F0–F5 portfolio research and monitoring; F1-A1B–F1-A1I.1 local/provider experiments; R3 blockers.  
**Trust:** GitHub identities and checked-in source were inspected directly for this checkpoint. Host-local reports and tests are attributed to the Codex/operator report and **have not been independently re-executed or hash-verified here**.

## 1. Immutable source identity snapshot

| Source | Exact identity | State / role |
| --- | --- | --- |
| `main` | `1574d83ab7c0ea0eebef22d0f2d00bc3ce2ed176` | Integrated baseline; no F1 GPU integration |
| [PR #42 — Portfolio finalization contract](https://github.com/publiomcko-cloud/defi-thesis-risk-copilot/pull/42) | `1edccc2173492d24ec3e227d918c0b9da9e34fd1`, based on `main` | Open, draft, unmerged; F0 handoff, completion contract and F0–F5 plan |
| [PR #43 — F1 synchronous Research Copilot](https://github.com/publiomcko-cloud/defi-thesis-risk-copilot/pull/43) | `b6b470ace24996ecf3d76d593362016eecd7cb28`, based on `main` | Open, draft, unmerged; F1 implementation/corrections |
| [PR #45 — Research-GPU policy and adapter](https://github.com/publiomcko-cloud/defi-thesis-risk-copilot/pull/45) | `0d9568e78ce414643cd86a86c19b4ae0ae0bbd79`, based on PR #43 HEAD | Open, draft, unmerged; F1-A1I and F1-A1I.1 |
| This checkpoint | Branch `docs/phase22-f1-doc-01-checkpoint-20261025`, parent `0d9568e78ce414643cd86a86c19b4ae0ae0bbd79` | Documentation overlay only; its eventual commit/PR identity must be read from GitHub |

**Integration order:** PR #42's scope/contract is a separate unmerged documentation proposal; PR #45 is stacked on #43. None of #42/#43/#45 is equivalent to `main`. Revalidate each ref before a consequential decision.

## 2. Authority and claim discipline

- **Implemented:** source exists at an exact commit; **tested:** evidence exists for the stated harness/environment; **reviewed:** reviewer identity, scope and independence are established; **approved:** an explicit owner decision covers precisely the enabled behavior. Never collapse these statuses.
- **Draft/unmerged:** does not authorize configuration, deployment, migration on production, route promotion, private-data transmission, rental, workers, scheduler, or release.
- **Provider experiments:** Vast.ai rentals were temporary, synthetic/public only; a successful GPU smoke or HTTP adapter mock does not prove an accepted Research Copilot.
- **Route/policy:** `report_synthesis.promotion.v3` remains authoritative for promotion. Experimental `report_synthesis.research_gpu.v1` is disabled by default, available only for isolated evaluation, and never promotional.
- **Research execution:** synchronous product contract remains 25 s backend / 30 s BFF abort / 35 s route maximum. The experimental 45 s request/30 s mean/120 s research policy does not activate a 120 s product operation.
- **Review:** Codex implementer and reviewer were the same session for the recent campaigns. No authenticated independent reviewer approval is established.

## 3. Phase F0–F5 and completion gates G0–G5

| Stage | Intended deliverable / acceptance | Current evidence and boundary | Status |
| --- | --- | --- | --- |
| F0 / G0 | Exact source/evidence handoff; owner-selectable release scope | PR #42 `docs/portfolio_f0_handoff.md`; R3 archives remain local, F0 notes partial recoverability; all R3 decisions pending | PARTIAL |
| F1 / G1 | Authenticated, attributable, persisted research with a **real approved** LLM, source/RAG validation and fallback | PR #43 candidate; PR #45 GPU evaluation-only v1. Qwen2.5 7B GPU inference observed during F1-A1H, but app request hit old 8 s timeout before quality assessment. F1-A1J five-case evaluation not yet run. | IMPLEMENTED CANDIDATE; REAL QUALITY UNPROVEN |
| G2 | Thesis/workspace, deterministic risk/stress, saved/reopen/compare/export, actual browser walkthrough | F1 candidate and earlier merged foundations; complete enabled-path owner GUI acceptance not yet recorded | PARTIAL |
| F2 | Temporal, lease, fencing, recovery and owner-signed execution safety | R3 historical H1–H7 open; ten R3.15 decisions pending; no qualified 120 s async architecture | BLOCKED FOR ACTIVATION |
| F3 / G3 | Safe scheduled thesis/watch evaluations, one-winner dispatch, in-app alerts | Phase 20C/20D foundations exist on main; actual enabled private worker/schedule path not qualified | BLOCKED FOR ACTIVATION |
| F4 / G4 | Enabled-path authenticated integration, source/tenant safety, PostgreSQL, deployment/browser evidence | F1-A1I.1 reported disposable PG16/17 migration and mock-HTTP success, not a live model run or deployed smoke; other R3 release gates pending | PARTIAL |
| F5 / G5 | Fixed release commit/digest, feature matrix, reproducible demo, independent challenge where claimed, explicit owner signoff | No accepted release candidate, no production activation of experimental code | PENDING |

**Intended portfolio milestones** from PR #42: `PORTFOLIO_DEMO_COMPLETE`, `PERSONAL_RESEARCH_READY`, `PERSONAL_RESEARCH_READY_WITH_MONITORING`, `PRODUCTIZATION_DEFERRED`. None is newly granted by this checkpoint.

## 4. F1 experimental chronology and evidence register

Locations below beginning `/home/publio/` are **original-host paths**, not GitHub-accessible proof. SHA-256 values are recorded from operator/Codex submissions; independent byte verification requires the originals. Any missing report, sidecar, or archive remains a provenance limitation.

| Stage | Report / source anchor | SHA-256 or key identity | Result and key limitation |
| --- | --- | --- | --- |
| F1 original/C1–C3 | PR #43: `docs/phase_22_f1_implementation.md`, implementation and correction reports with sidecars | GitHub PR #43 exact HEAD above | Candidate synchronous F1 + bounded fixes; default provider disabled |
| F1-A1B | `/home/publio/phase22-f1a1b-real-model-acceptance-20261023.md` | `02a65ccb8d5bc36bcdc8d42c64379a9f4e0c4009658ce86979191a632736c597` | Local Ollama real-model full evaluation 0/31; mostly 8 s timeouts; no acceptance |
| F1-A1C | `/home/publio/phase22-f1a1c-local-llm-feasibility-20261023.md` | `554730682831e85803ac41ddec63b128a1dfac930b596b17e470ce459d07b95a` | GPU layers active; five representative timeouts; isolated-local privacy not demonstrated |
| F1-A1D | `/home/publio/phase22-f1a1d-small-model-qualification-20261023.md` | `bf53b543008737fc3e1bd1fa1e5097880259900354bc23b2139dc25f02c67298` | Qwen 1.5B: 0/4 app cases; no quality acceptance |
| F1-A1E | `/home/publio/phase22-f1-a1e-vast-gpu-qualification-report.md` | `b6f02367050158207433e51b17b3f4f6ade8aff5c59b0ca356bd38bbe0ef06ec` | Vast create PUT ambiguous; no model test |
| F1-A1E-R | `/home/publio/phase22-f1-a1e-r-reconciliation-report.md` | `19e7eaa64447389f624e1fa72dec7dc1b711f439bef5a795c604f3130510f439` | Zero active instances/volumes in repeated checks; original PUT outcome not recovered |
| F1-A1E closure | `/home/publio/phase22-f1-a1e-new-campaign-complement.md` | `a9ceb2b37c1d8421b75b0fa1cbc367ac68a4328af2a54cba92c2c0c8fe4b6c39` | Operationally closed; historical ambiguity retained |
| F1-A1F | `/home/publio/phase22-f1-a1f-vast-5080-qualification-report.md` | `722e34f787908da5dc4894e759367d1466aefa28c77e4709e48fb59fc681f0d9` | Rental cleaned; SSH key rejected; model never tested |
| F1-A1G | `/home/publio/phase22-f1-a1g-ssh-correction-report.md` | `65072ead07efa592b5c6265660b0d232684acfd34cf9ea85fdd8ea4690ca92ed` | SSH correction and offline validation; no rental |
| F1-A1H | `/home/publio/phase22-f1-a1h-vast-ssh-corrected-report.md` | `ff3881d183a479d6a1eb14e42168a453b7ba351aa6be8ed48d51ba0142121a50` | SSH + RTX 5080 GPU inference succeeded; first app request hit 8 s limit; model quality UNTESTED; cleanup reconciled |
| F1-A1I | `/home/publio/phase22-f1-a1i-implementation-report.md` | `68c567e51a68f30ec4c6f005885b60372d55dca97c39156a9ac7ca79c57852a2` | PR #45 experimental policy implemented; no runtime authorization |
| F1-A1I.1 | `/home/publio/phase22-f1-a1i1-qualification-report.md` | `00031eb2c619407b413e0d24c8b52c50a272e5e208f4d1fc4c4b4125ac097d4e` | PG16.14 + PG17.11 migration 0037 reported PASS; mock HTTP adapter tests PASS; no live F1-A1J; no independent review |

**F1-A1I.1 detail (reported):** initial native Ollama nanoseconds overflowed INTEGER; migration 0037 now uses BIGINT for native-duration columns with SQLSTATE 23514 boundary tests (five invalid values). Existing historical records survived upgrade, and five synthetic GPU evaluation rows persisted. A downgrade removes v1-only columns/data; re-upgrade cannot resurrect them. The full backend suite was reported to reach 100% progress from **821 collected** without a final pass/skip count because of quiet output. Do not rewrite this as “821 tests passed.” Ruff was unavailable. No PostgreSQL outside the disposable PG16/17 test environment was touched.

## 5. R3 historical incidents — all PRESERVED_OPEN

| ID | Historical defect | Why it still matters |
| --- | --- | --- |
| H1 | Global-capacity failure, R3.13 | Worker/global capacity accounting |
| H2 | Vast cancellation-cleanup failure, R3.14 PG16 | Real provider worker cleanup |
| H3 | Organization-capacity failure, R3.14 PG16 | Cross-organization capacity |
| H4 | Vast lost-completion failure, R3.14 PG17 | Provider completion reconciliation |
| H5 | Vast cancellation time-eligibility failure, R3.14 PG17 | Worker lease and time |
| H6 | Intermittent SKIP LOCKED failure, R3.19 PG16 | PostgreSQL worker concurrency |
| H7 | Capacity failure on PostgreSQL clock rollback, R3.19 PG17 | Temporal consistency/recovery |

No earlier failed observation has been erased or accepted by this document. Historic R3.26–R3.31 archives remain host-local; PR #42's F0 handoff explicitly records evidence-access limitations, including no independently available standalone R3.32-R report in that recovery tree.

## 6. R3.15 protected-path owner decisions — all PENDING

**Owner decisions accepted in this checkpoint: 0 / 10.** The historical recommendation does not change status.

| # | Protected path | Historical disposition recommendation | Owner status |
| --- | --- | --- | --- |
| 1 | `.github/workflows/ci.yml` | DEFER_PENDING_EVIDENCE | PENDING |
| 2 | `.github/workflows/phase19-exercises.yml` | DEFER_PENDING_EVIDENCE | PENDING |
| 3 | `Dockerfile.backend` | ACCEPT_RECONSTRUCTED_SOURCE | PENDING |
| 4 | `backend/app/jobs/control_service.py` | DEFER_PENDING_EVIDENCE | PENDING |
| 5 | `backend/app/tests/test_phase21e_postgres_migration.py` | ACCEPT_RECONSTRUCTED_SOURCE | PENDING |
| 6 | `backend/app/tests/test_phase22_capacity_transition_atomicity.py` | DEFER_PENDING_EVIDENCE | PENDING |
| 7 | `docker-compose.yml` | ACCEPT_RECONSTRUCTED_SOURCE | PENDING |
| 8 | `docker-compose.production.yml` | DEFER_PENDING_EVIDENCE | PENDING |
| 9 | `docs/deployment.md` | ACCEPT_RECONSTRUCTED_SOURCE | PENDING |
| 10 | `backend/app/tests/test_phase21c_postgres_migration.py` | ACCEPT_RECONSTRUCTED_SOURCE | PENDING |

Protected source paths are **not** authorized for modification by F1-DOC-01. R3 time-floor and forward-clock-jump semantics remain owner decisions. Do not activate lease-bound workers or schedules.

## 7. Outstanding technical and governance gates

1. **F1-A1J real-model evidence:** separate owner rental authorization, current offer/cost check, verified SSH/host key, model digest, true cold-start evidence, five code-owned public/synthetic cases with 45 s request timeout and 30 s all-request mean, no provider failure and full inherited quality gates. A clean representative sample is not automatically a full-corpus pass or route promotion.
2. **Model route/private use:** current v1 evidence is nonpromotable; v3 remains the only live promotion authority. No third-party Vast GPU has `private_approved` status, and no private thesis transmission is authorized.
3. **Async 120 s architecture:** still requires approved idempotency, durable reservation, lease/fencing, cancellation semantics, atomic finalization, and safe recovery. Existing synchronous 25 s contract stays unchanged.
4. **PostgreSQL deployment/migration:** 0037 tested on disposable PG16/17 by Codex, **not** approved for a deployed database. Downgrade is destructive of v1-only evidence; back up/archive before any future downgrade and require separate deployment approval.
5. **Test evidence:** full backend quiet-output run has no exact pass/skip totals; lint Ruff was not run; live Ollama protocol and real cold start have not been observed on the new exact HEAD; no verified independent reviewer.
6. **R3 and release:** H1–H7 OPEN, 10 R3.15 decisions PENDING; F2/F3 temporal/security approval and G0–G5 release gates are not closed.
7. **Vast operational controls:** prior rentals were cleaned up by fresh instance/volume reconciliation; on-host Windows watchdog depends on host availability and is **not** a provider-enforced billing cap.

## 8. Next authorized vs pending work

**Current authorized development:** F1-A1I.1 technical qualification report and documentation reconciliation only; qualification is complete as reported. This checkpoint does not open any new spending or execution authority.

**Suggested next owner decision:** authorize **F1-A1J, one synthetic five-case real GPU evaluation**, after reviewing the exact pinned PR #45 head, operator environment, PostgreSQL scope, confirmed model identity, rental/cost/watchdog preflight, and safe destruction plan. A completed representative evaluation is quality evidence only; any 31-case run requires a new explicit decision if not covered by that authorization.

**Parallel later task:** F1-A1K async architecture design/implementation only after a separate owner decision, not as a prerequisite for the internal experimental five-case evaluation. F2/F3 activation remains blocked.

## 9. Recovery procedure and documentation stewardship

1. Fetch GitHub `main` at the exact SHA above, then read PR #42 `docs/portfolio_f0_handoff.md`, `portfolio_completion_contract.md`, and `portfolio_finalization_plan.md`.
2. Review PR #43 at exact HEAD for F1 implementation, citations, authorization, report lifecycle, and fixed 25 s execution.
3. Review PR #45 at exact HEAD for `research_gpu_policy.py`, `research_gpu_ollama.py`, migration `0037`, tests and `docs/phase_22_f1a1j_real_gpu_test_plan.md`.
4. Request original host-local reports only if direct evidence review is needed. Verify each byte-level SHA-256 and sidecar; no secret, SSH key, live DB dump or private thesis is required.
5. Read historical H1–H7 and ten R3.15 decisions from PR #42 F0, not from an assumed resolved status.
6. Before acting, recheck live GitHub HEADs, test/CI status, deployed-feature matrix, and any newer checkpoint. Do not silently reinterpret this snapshot as current after a ref changes.
7. To update: append a new dated checkpoint or versioned amendment with exact commit identities, documentary diffs, verified-vs-reported evidence distinction, changed decision statuses, and owner signoff. Preserve this snapshot as a historical record.

**F1-DOC-01 final verdict: `RECOVERABLE_DOCUMENTATION_CHECKPOINT_CREATED_WITH_EXTERNAL_EVIDENCE_LIMITS`.** No deployment, PR merge, R3 owner-decision acceptance, private model route, GPU rental, or scheduled worker activation is authorized by this file.
