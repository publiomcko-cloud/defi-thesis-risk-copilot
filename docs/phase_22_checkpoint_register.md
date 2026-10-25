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

## 9. Post-checkpoint review finding — F1-A1J runner acceptance logic

**Finding F1-DOC-01-R1 (pre-rental correction required):** The checked-in F1-A1J one-shot runner in PR #45 (source HEAD `0d9568e78ce414643cd86a86c19b4ae0ae0bbd79`, `docs/phase_22_f1a1j_real_gpu_test_plan.md`, lines 103–115) checks `run.status == "completed"`, `run.case_count == 5`, and `run.promotion_eligible == False`. The experimental policy intentionally forces `promotion_eligible=False` **regardless of quality**, while `status="completed"` can also describe failed cases. Thus the published command can exit successfully when zero of five cases passed. The document's prose specifies all-five quality acceptance, but the executable assertion does not enforce it.

**Required correction before any new GPU spend:** independently check `passed_case_count == 5`, `failure_reason is None`, zero provider failures, and complete required latency/token/native evidence; report per-case quality/latency and explicit `MODEL_QUALITY_FAILED` rather than treating `completed` as a successful candidate. Keep `promotion_eligible=False` (it is a non-promotable policy). Add focused tests for all-five-fail and partial-fail scenarios, without weakening v3 or changing evaluator labels. This is a targeted plan/runner defect, not a claim that the qualified PostgreSQL migration failed.

## 10. Recovery procedure and documentation stewardship

1. Fetch GitHub `main` at the exact SHA above, then read PR #42 `docs/portfolio_f0_handoff.md`, `portfolio_completion_contract.md`, and `portfolio_finalization_plan.md`.
2. Review PR #43 at exact HEAD for F1 implementation, citations, authorization, report lifecycle, and fixed 25 s execution.
3. Review PR #45 at exact HEAD for `research_gpu_policy.py`, `research_gpu_ollama.py`, migration `0037`, tests and `docs/phase_22_f1a1j_real_gpu_test_plan.md`.
4. Request original host-local reports only if direct evidence review is needed. Verify each byte-level SHA-256 and sidecar; no secret, SSH key, live DB dump or private thesis is required.
5. Read historical H1–H7 and ten R3.15 decisions from PR #42 F0, not from an assumed resolved status.
6. Before acting, recheck live GitHub HEADs, test/CI status, deployed-feature matrix, and any newer checkpoint. Do not silently reinterpret this snapshot as current after a ref changes.
7. To update: append a new dated checkpoint or versioned amendment with exact commit identities, documentary diffs, verified-vs-reported evidence distinction, changed decision statuses, and owner signoff. Preserve this snapshot as a historical record.

**F1-DOC-01 final verdict: `RECOVERABLE_DOCUMENTATION_CHECKPOINT_CREATED_WITH_EXTERNAL_EVIDENCE_LIMITS`.** No deployment, PR merge, R3 owner-decision acceptance, private model route, GPU rental, or scheduled worker activation is authorized by this file.

## 11. Addendum — F1-A1J five-case quality-gate correction (2026-10-25)

**Verified current candidate after this snapshot:** PR #45 head `a1c191ad79261b948f45a83e09c4a209b46f92de` (open/draft/unmerged), one commit after earlier `0d9568e78ce414643cd86a86c19b4ae0ae0bbd79`. Only three new changed paths in that commit: `backend/app/llm/research_gpu_readiness.py`, `backend/app/tests/test_research_gpu_readiness.py` and `docs/phase_22_f1a1j_real_gpu_test_plan.md`. The earlier source snapshot above remains the historical F1-DOC-01 anchor; use this addendum as its latest candidate pointer.

**Previously reported false-positive gate corrected in source:** the F1-A1J runner now calls `qualifies_as_approved_five_case_sample()` with persisted cases and enforces 5/5 passing cases, no provider failure, a null failure reason, complete metrics, exact v1 evidence binding, and latency boundaries while keeping `promotion_eligible=False`. Checked-in tests include 0/5, 3/5 and 5/5 fixtures and missing-observation/provider-failure examples. Codex reported ten targeted tests, compileall and diff-check passing, but no authenticated independent reviewer or hosted CI was evidenced. Plan SHA-256 supplied by Codex: `4670817063c754e58255b205fed8040b4ee4b750a70e1d2a2bbf01ff7d75d375` (host-local byte verification not independently performed).

**Open targeted false-negative risk (pre-rental):** the new read-only qualification helper at `research_gpu_readiness.py` rejects every warm case with `ollama_load_duration_ns != 0`. A warm, resident Ollama model can still report a small positive `load_duration`, so equality-to-zero is not a valid proof of warm residency. The evaluator's existing cold-start observation/phase mechanism is separate. Replace this requirement with runtime residency and phase evidence, retain the native duration as an observed, nonnegative metric and add a regression with positive warm `load_duration_ns`. Do not weaken case quality, token/timing completeness, cold-start verification or promotion boundaries. This fix can be included in the same explicitly authorized F1-A1J preflight rather than requiring another broad review.

**State:** No owner rental authorization is inferred. Phase 22 remains ACTIVE — HOLD; H1–H7 OPEN; ten R3.15 decisions PENDING. PR #45 is not merged and the experimental research-GPU policy remains non-promotable.

## 12. Addendum — F1-A1J digest namespace mismatch (2026-10-25)

**Observed campaign outcome reported by Codex:** F1-A1J rental instance `57691151` was created and destroyed; authenticated reconciliation reported zero active instances and volumes, an observable charge of USD 0.035, and unsettled final billing. Zero of the five evaluation cases were executed because the adapter compared the `/api/tags` digest beginning `845dbda0` with the approved digest beginning `2bada8a7`. The report is host-local at `/home/publio/phase22-f1-a1j-real-model-evaluation-report.md`, reported SHA-256 `3c19eee3020f1b442b2e1327138cfd0ef124dba9342d5f903c9ce1c69296432f`, and evidence-manifest SHA-256 `112e58d24362f3f644b023be04a48e7af52e9e1fceb23a95a5b8eadeef9e9fbc`. These locally reported checksums were not byte-verified here.

**Direct independent identification of the digest types:** The **official Ollama** model page at `https://ollama.com/library/qwen2.5:7b-instruct-q4_K_M` displays model/tag identifier prefix **`845dbda0ea48`**. The **model** blob linked on that same page (`https://ollama.com/library/qwen2.5:7b-instruct-q4_K_M/blobs/2bada8a74506`) displays **`2bada8a74506`** for the 4.7 GB Q4_K_M weight component. Thus the compared prefixes refer to **distinct SHA-256 namespaces for the same published Ollama model**: manifest digest versus GGUF model-layer/blob digest. The F1-A1J adapter currently compares a `/api/tags` **manifest digest** against a pinned **weights blob digest**, which is an invalid equality test. Full exact digest and manifest-layer linkage must still be verified using authoritative manifest bytes; prefix agreement alone is insufficient for execution approval.

**Classification correction:** `FIVE_CASE_REAL_MODEL_SAMPLE_FAIL_WITH_EVIDENCE` is the original operator's terminal label, but **not evidence that Qwen2.5 failed five cases**. The technically relevant status is `MODEL_IDENTITY_DIGEST_TYPE_MISMATCH_NO_CASES_EXECUTED`. Do not report 0/5 quality failures when zero cases ran.

**Next required step, offline only:** Retrieve the model's official registry manifest read-only; independently verify its raw manifest checksum and selected GGUF layer descriptor checksum against the two separately pinned expected digests. Check the observed full `/api/tags` digest from the redacted F1-A1J report rather than relying on an 8-character prefix. Implement a type-safe separation of manifest and weights-layer identities and focused success/rejection tests. Preserve original weight approval, dataset/prompt/policy authority, quality thresholds, and zero automatic promotion. **No additional rental is authorized by this addendum.**

**Source progression:** PR #45 was observed open/draft/unmerged at `5633715d16025a5e6d3ff827ac0ede9b144cce1c` after the F1-A1J warm-load fix. Phase 22 ACTIVE — HOLD; H1–H7 OPEN; ten R3.15 decisions PENDING.

## 13. Addendum — F1-A1J.1 verified manifest/weights identity correction (2026-10-25)

**PR #45 exact source identity at review:** `b029b4fc0920b147fe4683295ac8a3f58f099277`; open, draft, unmerged and based on PR #43. The corrected code now distinctly binds pinned Ollama manifest `sha256:845dbda0ea48ed749caafd9e6037047aa19acfcfd82e704d7ca97d631a0b697e` and model GGUF weights `sha256:2bada8a7450677000f678be90653b85d364de7db25eb5ea54136ada5f3933730`. The manifest source bytes are checked into `backend/app/llm/research_gpu_ollama_manifest.json`, with programmatic hash and layer validation in `research_gpu_ollama.py`. Runtime checks use the local, verified SSH-tunneled Ollama API (`/api/tags`, `/api/show`, `HEAD /api/blobs/{digest}`) and bind the exact tag/quantization/identity pair.

**Governance:** The experimental research policy and evaluator protocol are now **v2**, not v1. This is disabled by default, non-promotable and unrelated to `report_synthesis.promotion.v3`, which remains unchanged. 45 s request limit, 30 s mean and all strict quality and privacy requirements persist. The earlier digest-type mismatch is classified as an identity-contract defect, **not a model quality failure**. Prior F1-A1J 0/5 means **zero cases executed**, not zero cases passing.

**Reported validation:** 48 focused tests, compileall and git diff-check passed; the original-host report at `/home/publio/phase22-f1-a1j1-evidence/phase22-f1-a1j1-correction-report.md` has operator-reported SHA-256 `fb6a6921424f9461b7d5bc94bc04a3e58c94e64d2a9104ecf3a0ff7767bc458b`. The original report was not byte-read/verified in this GitHub-only checkpoint; neither live Ollama v2 nor a real cold start was independently tested by this reviewer.

**Next gate:** Explicit owner authorization for **one** F1-A1J retry with **exact five-case v2** evaluation, pinned source/model digests, safe public/synthetic fixtures, separate disposable PG database, one RTX 5080 rental and fully reconciled cleanup. Review and correct v1 prose in `docs/phase_22_f1a1j_real_gpu_test_plan.md` during the authorized execution, without altering code-owned policies. No rental, promotion, merge, private research or Phase 22 release is authorized by this documentation change.

**Standing state:** Phase 22 ACTIVE — HOLD; H1–H7 OPEN; all ten R3.15 decisions PENDING.
