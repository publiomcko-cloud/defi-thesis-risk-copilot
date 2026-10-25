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

## 14. Addendum — F1-A1J retry five real cases (2026-10-25)

**Execution result, reported by Codex/operator:** F1-A1J retry ran exactly the five code-owned real Qwen2.5 7B Q4_K_M cases at source `b029b4fc0920b147fe4683295ac8a3f58f099277` (PR #45, open/draft/unmerged). Five case-level records were persisted and **0/5 passed**; two cases had provider failures, three had output-field validation failures. The cold request measured **45,042 ms** against a 45,000 ms request limit; whether the model completed a reply or the HTTP client timed out is not established by that elapsed observation alone. The evaluator finalization threw `Research-GPU evaluation authority changed before completion`. Actual GPU utilization during inference was **not measured**. Therefore **no complete, authoritative passing evaluation run exists**, and no supported model-promotion claim follows.

**Cleanup and billing, operator-reported:** One instance only; authenticated subsequent checks found zero campaign instances and volumes; Windows watchdog, DPAPI copy and SSH campaign credential were removed. Latest visible Vast charge was **USD 0.044**, final settlement unconfirmed. No second rental, merge or production/private research activation. Original-host report `/home/publio/phase22-f1-a1j-retry-real-model-report.md`, operator-reported SHA-256 `7b4c640efd25260f014af46a7506e302d530bffd22c971a29170954af28c7d99`. The 47-file evidence manifest at `/home/publio/phase22-f1-a1j-retry-evidence/F1A1J-R2-20261025T171822Z-589fa238/evidence-checksums.json` is reported as SHA-256 `6f217c4ab6c017faa555cb51783bde0287a2d951aa001c75c4bfb2bf6c8a4cbc`. Host-local bytes/manifest have not been independently inspected in this GitHub-based review.

**Source-level diagnostic finding, not yet established as the unique runtime cause:** At reviewed PR #45 HEAD, `backend/app/llm/evaluation.py`'s `_research_gpu_binding_is_current` rejects **any** persisted case row whose native Ollama durations or provider-observation timestamp is `None`, using `all(value is not None ...)` over every case. A genuine provider timeout can yield no Ollama response, and `VerifiedResearchGpuOllamaProvider.generate` clears `last_observation` before the HTTP call. In that circumstance the absent native metrics are persisted, and this guard returns false, producing the same misleading generic `authority changed before completion` even when immutable model/prompt/dataset authority did not change. **A missing observation must disqualify the case and whole sample, but it should not automatically be classified as authority tampering.** Verify all authority predicates and persisted rows against the existing five-case evidence before assigning a definitive root cause. The current evaluator also overrides a missing-observation case's `reason_code` with `runtime_evidence_invalid`, which can obscure the original failure class.

**Next action recommended:** **No new GPU rental.** Perform one bounded, offline evidence forensics using the existing 47 files and isolated evaluation database: report each case's true outcome, reason, timings, token/native-observation availability and privacy-redacted output-schema differences. Distinguish HTTP deadline from actual native model timing, investigate missing or changed binding predicates without rerunning inference, and establish whether GPU execution really occurred (record `NOT_MEASURED` if past proof is absent). If a narrowly scoped code fix is supported, preserve failed-case evidence and allow unsuccessful but authority-consistent runs to finalize as non-promotable failed evaluations, while retaining strict qualification requiring all measurements and 5/5. Tests must cover provider timeout with missing native metrics and genuine authority mutation. Do not change latency policy, prompts, quality gates or model identity before evidence-backed owner decision.

**State:** Phase 22 ACTIVE — HOLD; H1–H7 OPEN; all ten R3.15 decisions PENDING. F1-A1J retry verdict remains `FIVE_CASE_REAL_MODEL_SAMPLE_FAIL_WITH_EVIDENCE`, with incomplete evaluator finalization. This is not a passed model qualification.

## 15. Addendum — cold-timeout phase desynchronization hypothesis (2026-10-25)

At source `b029b4fc0920b147fe4683295ac8a3f58f099277`, `VerifiedResearchGpuOllamaProvider.generate()` sets `last_observation=None` before calling Ollama and only clears `_cold_request_pending` **after a successful HTTP response**. If case 1 times out, `_cold_request_pending` remains true. The next successful call may then be labeled `cold` by the adapter while the five-case evaluator expects `warm` for every case after the first, and its mismatch path sets `provider_failure=True` and overwrites `reason_code="runtime_evidence_invalid"`. This is a concrete **conditional** mechanism for an apparent second provider failure, not proof that it occurred in the historical run. Inspect retained per-case native records and logs before asserting the cause. A timeout before output does not establish that remote generation ended, so do not silently reclassify a later call as warm. Preserve accurate cold-state uncertainty and fail the sample safely without creating spurious upstream-failure claims. Add focused timeout→next-case tests only if a bounded correction is authorized; do not start a new rental for diagnosis.

## 16. Addendum — F1-A1J-R3 offline attribution (2026-10-25)

**PR #45 updated exact HEAD:** `4d652e74b5fe2b8d8e9bea0ad88a109409f9b95e`, open, draft and unmerged, based on PR #43. Original F1-A1J retry report and 47-file manifest hashes were **confirmed by the executing Codex**; this documentation update has not independently accessed those original host-local bytes. PostgreSQL evaluation database was already removed; attribution used persisted export evidence.

**Observed attribution:** Three generated outputs were syntactically valid JSON but rejected for incorrect top-level keys; the concrete key names were not retained, so further schema-specific claims cannot be reconstructed. The `risk_mutation` provider-failure classification resulted from cold/warm phase desynchronization and was **not** an established upstream provider failure. For `ordinary_valid`, HTTP timeout is plausible but unproven because HTTP status/exception information was not captured. No genuine semantic model-quality failure has been independently proven. GPU utilization and CUDA execution during inference were **NOT_MEASURED**. Keep historical 0/5 observed outcome but do not equate it to five semantic failures.

**Bounded corrections at PR #45 HEAD:** Missing native runtime metrics now disqualify an evaluation without being mistaken for immutable authority tampering. Original reason codes are preserved, and a failed cold request forces subsequent generation to fail closed until runtime reverification. Exact source inspection also confirms `_evaluate_case()` returns `provider_call_made` and `provider_call_state`; do **not** register that field as a missing-code defect. Reported validation: nine targeted tests, `compileall` and Git whitespace check passed; no complete regression or independent authenticated review. Original-host report `/home/publio/phase22-f1-a1j-r3-offline-diagnostic-report.md`, operator-reported SHA-256 `0a2799593b319722fce5db5a74bba4c1b9bd37c2ad60a05c8b9788d3529b15d5`.

**Next bounded recommendation (offline only):** The current Ollama adapter uses `format: "json"` in `POST /api/generate`; Ollama officially documents passing a JSON Schema object to `format` for constrained structured output. Implement a schema-constrained **evaluation-only** request matching the app's existing top-level `executive_summary` and `sections` validator, keep the validator as final authority, and version/bind changed experimental request protocol so its evidence is not confused with the old v2 protocol. Confirm that unknown/extra keys cannot be accepted, avoid rewriting historic failed outputs, add tests for malformed/mismatched JSON and exact request shape, and preserve rejection metadata without saving sensitive raw outputs. No new rental, prompt relaxation, promotion-v3 modification or 31-case execution is authorized.

**Standing state:** Phase 22 ACTIVE — HOLD; H1–H7 OPEN; ten R3.15 decisions PENDING. No new owner authorization for a paid run is implied.

## 17. Addendum — F1-A1J-R4 structured-output policy v3 (2026-10-25)

**Exact source:** PR #45 at `5b5f0c63b1a198f7127aac94986b6c70761b362f`, based on PR #43, still open, draft and unmerged. The GitHub PR endpoint showed `mergeable=true` at this review; the earlier Codex observation `mergeable=false` is not an active integration blocker here, but no merge is authorized.

**Change confirmed in source:** The research-only `VerifiedResearchGpuOllamaProvider` sends an object JSON Schema as `format` to Ollama `POST /api/generate` with `stream=false`. It requires exactly the top-level keys `executive_summary` and `sections`, restricts sections to a code-owned subset of six allowed titles and uses `additionalProperties=false`. The normal `OllamaProvider` still sends `format="json"`. Final `_validate_synthesis_payload` and semantic controls remain authoritative; no auto-repair or retry is added. The exact code-owned experimental versions are `report_synthesis.research_gpu.v3`, `report_synthesis.research_gpu_evaluator.v3`, and `report_synthesis.research_gpu_binding.v3`. Codex-reported experimental policy checksum: `e8aa666edf9e3c559372a1cb6287876cafa587aec3b3fc7ca87c002779be160f`. Promotion-v3 and the latency/quality thresholds were not modified by this diff.

**Reported validation and limitations:** Codex reports 72 focused and 9 readiness tests passing, `compileall` and `git diff --check` passing; three preexisting test expectations were updated for incomplete-measurement classification. No actual v3 Ollama inference, fresh PostgreSQL test, new paid rental, hosted CI conclusion or independent authenticated reviewer has been demonstrated here. The original-host report `/home/publio/phase22-f1-a1j-r4-structured-output-correction-report.md` has Codex-reported SHA-256 `fdea501d5b5656137fdb00263c4d45174356c884ae8264c7b2a7c24b82aa6374`; its local bytes were not directly read here.

**Owner decision pending:** One prospective and separately authorized F1-A1J-R4 real-GPU sample of exactly five public/synthetic cases, pinned manifest/weights digests, isolated PostgreSQL and verified SSH tunnel, 45 s provider request timeout and 30 s mean, five of five passing cases, GPU offload and CUDA utilization measurements where observable, historical-grade cost/cleanup reconciliation, and no 31-case run. The strict first-cold-request 45 s limit may remain a constraint: the earlier measured 45,042 ms wall time cannot prove a native Ollama timeout, but it is insufficient as passing latency evidence. Do not silently prewarm, omit cold latency, loosen limits or run extra model requests to force a pass. The existing F1-A1J plan also retains one stale concluding phrase saying `v1` even though the active experimental source and its binding are v3; this is documentary drift, not permission to execute v1. No owner spending approval or live evaluation has been granted by the checkpoint.

**Standing status:** Phase 22 ACTIVE — HOLD; H1–H7 OPEN; all ten R3.15 owner decisions PENDING. PR #42/#43/#45/#46 remain unmerged in the evidence reviewed.

## 18. Addendum — F1-A1J-R4-GPU no-rental preflight (2026-10-25)

**Campaign result, as reported by Codex/operator:** `RENTAL_NOT_STARTED_WITH_EVIDENCE`. Zero instances created and **zero** evaluation cases attempted; this is **not** a 0/5 model-quality result. PR #45 remained at `5b5f0c63b1a198f7127aac94986b6c70761b362f` with a clean checkout; experimental v3 policy checksum `e8aa666edf9e3c559372a1cb6287876cafa587aec3b3fc7ca87c002779be160f` and the earlier R4 report checksum were confirmed by Codex. Read-only Vast authentication worked; listing returned zero instances and zero volumes. `instance_write` scope was visible, but **no live create/delete action exercised**; this is permission evidence, not end-to-end teardown proof.

**Operational blockers, all before spending:** No registered/account-visible SSH public key (profile `ssh_key` absent); only an old, disabled watchdog for a different campaign; no isolated evaluation `DATABASE_URL`, `F1A1J_OPERATOR_USER_ID`, or prepared Python interpreter importing SQLAlchemy. Do not reuse a disabled historical watchdog or access another project's DB. An isolated project virtual environment and disposable PG16/17 evaluation database with an approved local test-administrator identity are needed. The system Python missing SQLAlchemy is an environment-selection problem, not proof the application dependencies are invalid.

**Permissions distinction:** Vast's official permissions reference (`https://docs.vast.ai/api-reference/permissions`) associates `instance_write` with instance create/manage/delete and instance SSH-key attachment, `user_read` with viewing account SSH keys and `user_write` with registration/editing/removal of account SSH keys. Lack of `user_write` on an execution key may require the owner to register the ephemeral public key through the web console or a separately approved credential; do not elevate access by default. Distinguish account key read-back from an SSH key attached to an instance.

**Offer observation, not a reserved instance:** Codex reported verified full RTX 5080 offer `#57701035`, 16,303 MiB, reliability 99.89172%, CUDA 13.0, DLPerf 83.6399, and an estimate for 20 GB disk of USD 0.365556/hour or USD 0.182778 for 30 minutes **before network fees and billing adjustments**. This is a snapshot only; price, availability, attached storage and the offer's actual full-GPU allocation must be rechecked before any newly authorized rental. No GPU consumption occurred in this campaign.

**Host-local report:** `/home/publio/phase22-f1-a1j-r4-gpu-qualification-report.md`; Codex-reported and sidecar-checked SHA-256 `8129278e12d960dd3bc707727de09f069c0ca37eafd1ecd26cb6fd2e07abc84d`. The report's bytes were not independently materialized and hashed by the present GitHub review.

**Next action recommended:** Prepare and prove all missing prerequisites **offline, without a Vast rental**: ephemeral scoped SSH public-key registration/read-back (only with authorized account write access), clean campaign-specific watchdog dry-run under a harmless synthetic instance ID and bounded API reads, project-scoped Python import/preflight, disposable PG evaluation schema at migration 0037, active local-only platform-admin identity, and a redacted one-command readiness matrix. Never run a destructive API probe against arbitrary resources. Preserve the explicit separation between operational-preflight readiness and authorization to incur charges. No new instance or paid inference is authorized by this addendum.

**Phase state:** ACTIVE — HOLD; H1–H7 OPEN; ten R3.15 owner decisions PENDING. PR #45 and documentary PR #46 remain draft and unmerged as reviewed.

## 19. Addendum — F1-A1J-R4 offline preflight qualification (2026-10-25)

**Operator/Codex verdict:** `BLOCKED_WITH_EXACT_ACTIONS`, no GPU rental or model request. PR #45 HEAD `5b5f0c63b1a198f7127aac94986b6c70761b362f` was checked clean and unchanged; still open/draft/unmerged. The preflight report is host-local `/home/publio/phase22-f1-a1j-r4-preflight-report.md`, with operator-reported and sidecar-verified SHA-256 `6837828390ac84666799fdea7f18fa58c5cd66073eaef881ce2055d97ab99b3f`. Single-command preflight lives at `/home/publio/.codex/phase22-f1a1j-r4-preflight/preflight.sh`. These host-local files were not independently materialized or hashed for this documentation addendum.

**Offline prerequisites that passed (operator evidence):** Project Python runtime including SQLAlchemy and required imports; disposable, loopback-only PostgreSQL 17.11 upgraded through `20261025_0037`; a validated synthetic local platform administrator. The evaluation database was prepared, not a production database. Authenticated Vast GETs succeeded and returned zero instances and volumes. A Windows Scheduled Task ran a preflight as user `PUBLI`; all eight simulated watchdog cases passed, with no real DELETE.

**Remaining owner controls, not defects of application source:** The locally prepared ephemeral public SSH key with fingerprint `SHA256:ZZYkhRjEvoLwp1lswpX8tpY2Oxsdpr3ky3HQrrs0yLc` was **not** registered in the Vast account. The active token's ability to perform instance creation/destruction is **not proven** by GET success or a permission label, since no real write/delete request was issued. The preflight Windows task is ready, but the campaign-specific `Watch` mode is **not armed**, because no authorized rental, specific instance ID, or deadline exists. It depends on a running Windows machine and logged-in session; neither absolute billing cap nor independent-host guarantee is claimed. Do not create a dummy instance merely to validate rights.

**Minimal owner actions:** (1) Register the exact local campaign **public** SSH key in Vast by explicitly approved account UI or limited `user_write` API action and read back its matching fingerprint through `user_read`, without exposing the private key. Vast account registration may propagate to existing instances; distinguish it from per-instance SSH-key attachment, which is covered by `instance_write`. (2) Provide an approved **scoped** management API token supporting `instance_read`, `instance_write` and, as needed, `user_read`/`misc` and billing read; do not publish or log tokens. Revalidate effective scopes through non-destructive operations. (3) Re-run the existing single-command preflight. If all PASS, request **separate owner authorization** for a one-instance, five-case v3 GPU campaign; only after creation can the watchdog be bound and armed with that actual instance ID and fixed destruction deadline. Watchdog disarm/credential cleanup only after destruction and resource reconciliation.

**Offer snapshot only:** Historical observed offer `#57701035` was a verified full RTX 5080, about 16,303 MiB VRAM, with a quoted ~USD 0.365556/hr inclusive 20 GB disk and ~USD 0.182778 for 30 minutes before transfer, additional charges or billing rounding. This is not reserved or currently guaranteed; all prices and host identity require fresh verification before any rental.

**Safety and status:** There was **no rental** and **zero cases attempted**; do not mark the Qwen candidate as 0/5. No new source modification, PR merge, route promotion or private-data run was authorized. Phase 22 remains ACTIVE — HOLD; H1–H7 OPEN; ten R3.15 decisions PENDING.

## 20. Addendum — R4 preflight SSH registered (2026-10-25)

**Updated owner/Codex preflight result:** The re-run of `/home/publio/.codex/phase22-f1a1j-r4-preflight/preflight.sh` still reported `BLOCKED_WITH_EXACT_ACTIONS`, but **the campaign SSH public key is now registered**: the account read-back matched the existing prepared public-key fingerprint `SHA256:ZZYkhRjEvoLwp1lswpX8tpY2Oxsdpr3ky3HQrrs0yLc`. This resolves the SSH registration blocker recorded in section 19 without changing the key or source.

**Passed again, as reported by Codex:** PR #45 exact HEAD `5b5f0c63b1a198f7127aac94986b6c70761b362f` and clean tree; project Python dependencies/imports; isolated PostgreSQL 17.11 and revision `20261025_0037`; synthetic administrator; Windows Scheduled Task and mock cleanup cases; Vast authenticated listings report zero instances and volumes. No rental, model inference or instance write/delete request was made. The previously checksummed preflight report was **not amended** and therefore still documents the previous, absent-SSH state. Do not quote the old report as proof of SSH still being absent.

**Remaining gate:** Verify that the executing management API key has the **effective `instance_write` scope** as documented by Vast (`https://docs.vast.ai/api-reference/permissions`), without a dummy create or DELETE; positive GETs prove only read permission. Runtime ability to create/destroy cannot be fully tested non-destructively and must be handled fail-closed during a separately authorized paid campaign. The already-prepared Windows watchdog is intentionally **not armed**: its Watch mode needs the actual, owner-authorized instance ID and destruction deadline. It must be armed immediately after successful instance creation and cleaned up only after destruction/reconciliation. If Watch cannot be armed, destroy that instance immediately; if creation result is ambiguous, reconcile before taking any new action. No second rental or new automated cleanup authorizations are implied.

**Owner authorization still required:** An explicit, separately bounded one-instance Vast RTX 5080 rental approval before creating a paid resource. Preserve the v3 five-case policy, 45 s individual timeout and 30 s mean, no private data, no 31-case run, no route promotion/merge, and the Phase 22 ACTIVE — HOLD / H1–H7 OPEN / R3.15 PENDING states.

## 21. Addendum — F1-A1J-R4 authorized attempt stopped before rental (2026-10-25)

**Operator result:** `RENTAL_NOT_STARTED_WITH_EVIDENCE` / `BLOCKED_WITH_EXACT_ACTIONS`. The subsequent owner-authorized **single attempt** stopped at permissions and Watch preflight, **before any instance creation**. Authenticated Vast GETs returned zero instances and volumes, and account SSH key read-back continued to find the registered F1-A1J public key. **Zero cases were attempted; this is not a Qwen quality score of 0/5.** Incremental resource charges for this attempt were reported as **USD 0**; no instance create/delete or model download/inference action occurred.

**Confirmed blocking facts:** The observed execution token rights showed GET instance endpoints but did **not** establish `instance_write`, the Vast authorization category that covers creating, managing and destroying instances/volumes. A registered, enabled Windows task exists only for `Preflight`; no new-campaign `Watch` task was registered. The Watch cannot be **armed** until an actual, separately authorized instance ID and destruction deadline exist, but its **inert template, independent scheduler registration, dry-run and atomic arm procedure** must be prepared/verified in advance, without deleting resources. A GET response does not prove effective instance write/delete capability; do not create a dummy rental solely to prove it.

**Evidence:** Codex-reported local final attempt report `/home/publio/phase22-f1-a1j-r4-gpu-final-attempt-report.md`, reported and sidecar-checked SHA-256 `2aeb3017832cff555a4894dade137255b59e16b10573fa0726e5cd468c0dc904`. No independent local file byte inspection in this GitHub-only checkpoint.

**Next exact owner/operator actions:** Use Vast **Keys → API Keys** to inspect the token actually used by the execution environment. If `instance_write` is missing, create a **dedicated, scoped** execution token with `instance_read`, `instance_write`, `user_read`, `misc` and the minimum necessary billing read permissions. Avoid `user_write`, `billing_write` and broad account permissions. Supply the token securely to the runner and independent watchdog using protected local credential mechanisms; never add tokens to chats, Git or checksummed plaintext. Independently prepare a **new R4 Watch task** in a disabled/unarmed state, verify scheduled-task identity and mock teardown handling, and document how it will be armed with actual ID/deadline **immediately after creation** and before downloads/inference. If Watch arming fails after instance creation, destroy/reconcile that instance immediately. Windows-offline/session-dependency remains an explicit residual risk.

**Control boundary:** No new rental is authorized by this documentation update. The previous single-attempt approval was exercised for the preflight which terminated without renting. Seek separate explicit owner approval for any further paid-resource creation after the scopes/Watch readiness are proven. PR #45 source remains `5b5f0c63b1a198f7127aac94986b6c70761b362f` open/draft/unmerged; PR #46 remains documentation-only. Phase 22 ACTIVE — HOLD; H1–H7 OPEN; ten R3.15 decisions PENDING.

## 22. Addendum — F1-A1J Windows watchdog preflight destructive-path incident (2026-10-25)

**Owner/Codex incident report:** The Vast account token used by the local R4 runner was confirmed to **have** `instance_write`: the preflight incorrectly treated the per-route `rights.api["*"]` list (GET-only instance routes) as more authoritative than the category grants in `rights.api`. Local preflight-only code `/home/publio/.codex/phase22-f1a1j-r4-preflight/preflight.py` was reportedly fixed, syntax-checked and hashed to SHA-256 `31f343fa63feafb976c648bbf9023690db7d91dc0ab223479dc832ab226cc20c`. Source change is host-local and **not** independently inspected here. The used token was identified through an authenticated account read-back as account key ID `34409649`, named `codex - defi`, with a redacted fingerprint prefix `46d3fbcc4d79683991aa`. Its observed grants included `instance_read`, `instance_write`, `user_read`, `user_write`, `misc`, `billing_read`, and `billing_write`: **least privilege is not satisfied**. No Vast write request, GPU rental or inference occurred.

**Destructive local-host incident:** During attempted preparation of a new Windows Watch task, WSL subprocess environment variables did not propagate into PowerShell. An empty-path error handler reportedly executed an unsafe recursive removal of `C:\Users\PUBLI\AppData\Local\Phase22\F1A1J`. This erased the old preflight folder and content including `cleanup.ps1`, `watchdog.log`, and a DPAPI-protected credential copy, plus an older campaign log stored under the same root. This is an unintended local filesystem deletion and a **material audit-evidence loss**, not an instance deletion or proof that the old credential was mismatched/compromised. The previous DPAPI key-fingerprint comparison was inconclusive. Do not conflate missing files with verified destruction of a secret from other locations. Historical reports elsewhere remain but the Windows local audit trail is incomplete.

**Current task status:** The old Windows Scheduled Task was disabled, pointing to a nonexistent script. **No new Watch task exists** or was armed. The previous checksummed preflight report remained unmodified and is **stale** with respect to Watch readiness. The source repo PR #45 is unaffected by this incident, but the operator reports that another initially opened local checkout had **preexisting changes in documentation/scripts**; do not reset, clean, stage, discard or move those files. The main evaluation policy and PR #45 are not changed by local Watch operations. The Phase 22 project remains ACTIVE — HOLD; H1–H7 OPEN and all ten R3.15 decisions PENDING.

**Mandatory targeted recovery and prevention before further account operations or paid resources:**
1. **Freeze destructive cleanup and new Watch registration** on the affected Windows path. Capture event/transcript/task records available non-destructively. Determine whether File History, Previous Versions/VSS or independently stored backups can restore missing script/log/DPAPI artifacts, preferably **to a separate destination**; if not, log an explicit non-recoverable audit gap. Limit writes to the affected drive until recovery feasibility is assessed. Windows File Recovery, if used with owner approval, must use a distinct output drive.
2. Root-cause and remediate the WSL→PowerShell argument/environment contract, validate required variables and resolve canonical nonempty paths **before any filesystem mutation**, reject directories above the per-campaign leaf, prohibit recursive deletion of the shared `Phase22\F1A1J` root, reject path wildcards/reparse-point escape, use exact allowlisted file cleanup and dry-run/fault-injection tests. A failed command should fail closed and **not** invoke an alternative cleanup based on an empty path.
3. Create a new, isolated campaign identifier and **unarmed/disabled** Watch only after the destructive-path regression has passed and owner-controlled recovery decision is recorded. Verify independent scheduler identity, protected credential re-encryption/fingerprint match, mock teardown and effective task state. The real Watch can be armed only using an owner-authorized actual instance ID and UTC deadline.
4. Correct least privilege: use a dedicated execution key with needed instance and read scopes, without `user_write`/`billing_write`, rotate/store it under protected credentials with an explicit owner action; **do not revoke working access prematurely** before a verified replacement. Never expose tokens or private keys in Git, logs or chat.

**Standing decision:** `BLOCKED_WITH_RECOVERY_AND_SAFETY_CORRECTION`. This documentation action does **not** authorize restoring/deleting local files, modifying Vast account keys, creating instances, or paid inference. The single previously authorized rental attempt stopped without creating a resource. A new paid-resource attempt requires explicit separate owner authorization after remediation and a fully passing preflight.

## 23. Addendum — Windows Watch incident offline correction and owner recovery decision (2026-10-25)

**Codex/operator verdict:** `INCIDENT_CORRECTION_READY_FOR_OWNER_RECOVERY_DECISION`. The accidentally removed Windows tree `C:\Users\PUBLI\AppData\Local\Phase22\F1A1J` remains absent. Reported SHA-256 of the host-local checksummed investigation: `a2ee60d9c369f4bd1833a6bc1aa15f0de98b4fe9c776d9cb56c637e8169ea84b` at `/home/publio/phase22-f1-a1j-r4-incident-recovery-report.md`. This GitHub-only update has not directly read/hashed the host-local investigation.

**Cause/evidence:** WSL-exported variables were not forwarded to PowerShell; an empty campaign ID made the cleanup destination collapse to the shared `F1A1J` root, and an error path called recursive removal. The sequence is supported by operator execution logs, **not** a preserved/hash-verified copy of the original inline script (lost). Known missing files include `cleanup.ps1`, `register-task.ps1`, `watchdog.log`, `campaign.json`, `vast-api-key.dpapi` from the R4 tree and a previous campaign's `watchdog.log`. No complete original file manifest existed, so this is a minimum missing inventory, not an exhaustive count. A lost DPAPI *copy* is not by itself proof that the active API token has been compromised or revoked.

**Recovery state:** Operator found no replacement in inspected local backups, focused search `/mnt/e/projetos/phase22-recovery`, File History or Recycle Bin. CIM did not show shadow copies, but `vssadmin` and `wbadmin` could not obtain authoritative results without elevation; lack of a verified VSS/backup snapshot is **not** proof of permanent loss. Nothing was restored. Old Windows task is disabled and references a missing script; no new Watch was registered or armed.

**Source-local safety correction:** New host-local safety code at `/home/publio/.codex/phase22-f1a1j-r4-incident-recovery/watchdog_safety.py`, `watchdog_preflight.ps1`, and `test_watchdog_safety.py` passes 12 discardable-directory tests under `/tmp`, Python compilation, and PowerShell parse validation **as reported by Codex**. It specifies explicit PowerShell arguments, validates nonempty absolute canonical paths confined to the per-campaign leaf, rejects wildcards/reparse points, is dry-run-only, and disables destructive error cleanup. No restored Windows tree, actual Watch task, or real Vast DELETE was produced by these tests. Local repository checkout/PR #45 were not modified; preexisting unrelated doc/script changes in an opened checkout remain owner-protected.

**Single next owner decision:** Run **read-only** elevated inventory from a Windows Administrator PowerShell on the affected machine: `vssadmin list shadows /for=C:` and `wbadmin get versions`, followed by `wbadmin get items -version:<exact listed version>` **only if a relevant backup version appears**. These list operations do not restore/delete snapshots. The command `wbadmin get versions` requires elevation and can list local backup catalog entries that are no longer accessible; existence of a version identifier is not proof that recoverable files exist. If a relevant snapshot/backup exists, inspect source/date/file entries and request specific owner approval **before copying/restoring**, preferably to a separate location. If nothing is recoverable, record the Windows watchdog-log audit gap as unresolved/lost without manufacturing historical logs; optional forensic file-recovery with an external destination is separately approved and never a prerequisite for acknowledging the incident.

**Next operational boundaries:** Do not recreate the deleted `F1A1J` root or register a Watch until the owner has decided how to handle recovery and the safe path/argument code has passed a final targeted review. Rebuild under a new isolated campaign path, with protected least-privilege API credentials, verified Windows Scheduled Task in **unarmed** state, and fault-injection of WSL→PowerShell missing arguments. No paid GPU rental, model inference, unsafe recursive removal, account-key modification, PR merge or Phase 22 release was authorized by this checkpoint.

**Standing state:** Phase 22 ACTIVE — HOLD; H1–H7 OPEN; ten R3.15 decisions PENDING. PR #45 HEAD `5b5f0c63b1a198f7127aac94986b6c70761b362f` open/draft/unmerged; PR #46 remains docs-only.
