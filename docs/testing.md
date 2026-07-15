# Testing — DeFi Thesis & Risk Copilot

## 1. Testing Goals

Testing should validate:

- backend API behavior
- risk scoring consistency
- RAG retrieval quality
- report generation structure
- data adapter fallbacks
- frontend build quality
- Docker configuration
- source monitoring and evaluation workflows
- simulation, watchlist, and alert logic
- options analysis
- optional LLM synthesis fallback behavior
- ML groundwork guardrails
- HPC template syntax
- Phase 10 discovery-to-RAG ingestion safety
- Phase 11 access control and credential isolation
- Phase 12 Vast.ai lifecycle safety
- Final Phase 13 demo seed idempotency and safety

## 2. Baseline Validation

Run before and after each phase:

```bash
cd backend
source .venv/bin/activate
python -m pytest -q
python scripts/run_smoke_checks.py

cd ../frontend
npm run lint
npm run build

cd ..
docker compose config
docker compose -f docker-compose.production.yml config
```

## 3. RAG Validation

```bash
cd backend
python scripts/build_retrieval_eval_dataset.py
python scripts/evaluate_retrieval.py --retriever hybrid
python scripts/evaluate_retrieval.py --retriever hybrid_semantic
```

The retriever should return relevant protocol chunks and preserve citation metadata.

## 4. ML Groundwork Validation

```bash
cd backend
python scripts/export_training_dataset.py
```

Tests should confirm exported labels are deterministic-rule labels, not human ground truth, and that baseline classifier output cannot override deterministic risk scoring.

## 5. HPC Template Validation

Phase 9 HPC files are optional templates. Local validation should check syntax and preserve normal app behavior:

```bash
bash -n hpc/slurm_generate_embeddings.sbatch
bash -n hpc/slurm_evaluate_retrieval.sbatch
bash -n hpc/slurm_train_risk_classifier.sbatch
test -f hpc/apptainer.def
```

Actual `sbatch` submission and `apptainer build` depend on cluster tooling and are not required for local MVP validation.

## 6. Phase 10 — Discovery to RAG Ingestion Tests

Tests should validate:

- DefiLlama protocol discovery normalizes candidates
- DefiLlama pool discovery normalizes candidates
- options/open-interest discovery can be enabled separately
- discovery filters exclude low-quality candidates
- duplicate discoveries are not recreated
- every candidate starts as `needs_review`
- automatic evaluation creates a review item
- `needs_review`, `rejected`, `needs_more_data`, and `archived` items cannot be ingested
- only `approved_for_rag` items can be ingested
- ingestion requires an explicit action
- generated markdown includes source URL, protocol, risk summary, missing data, reviewer notes, and disclaimer
- duplicate ingestion is prevented
- RAG index refresh is triggered after ingestion
- future retrieval can find the ingested source

## 7. Phase 11 — Access Control and Credential Tests

Implemented Phase 11 tests cover the MVP bearer-token access-control path, admin/common role boundaries, server-side credential metadata, and audit logging.

Tests should validate two roles:

```text
admin
common
```

Common-user tests:

- can create analysis requests
- can run simulation and options analysis
- can manage own watchlist items if ownership is implemented
- cannot approve review items
- cannot ingest into RAG
- cannot configure discovery sources
- cannot create/update/delete provider credentials
- cannot start/destroy Vast.ai sessions

Admin-user tests:

- can pass admin-only dependencies with a valid admin token
- can approve/reject review items
- can ingest approved items into RAG
- can create/rotate/delete provider credentials
- all sensitive actions create audit-log entries

Vast.ai session authorization is tested in Phase 12 after those endpoints exist.

Credential tests:

- full API keys are never returned by API responses
- full API keys are never rendered in frontend payloads
- persisted credentials are encrypted or stored only through environment variables
- provider metadata can show provider name, status, and last four characters only
- deleted/rotated credentials cannot be used again
- missing `CREDENTIAL_ENCRYPTION_KEY` fails closed for database-stored secrets

## 8. Phase 12 — Vast.ai Provider Tests

Do not call real Vast.ai APIs in unit tests.

Use mocks/fakes to validate:

- offer search request shape
- max hourly cost guard
- GPU/RAM/disk filters
- create/rent lifecycle state transitions
- disabled provider safe error
- no acceptable offer produces `offer_not_found`
- max active instance limit
- OpenAI-compatible model endpoint call once ready
- auto-destroy after successful task
- cleanup after failed startup
- cleanup endpoint destroys known active instance
- destroy is idempotent
- raw API key is never returned
- common users cannot access Vast lifecycle endpoints
- admin actions are audit-logged
- remote LLM output cannot override deterministic risk scoring

Current automated tests use dry-run and fakes only. Integration tests against real Vast.ai should be manual/admin-only and disabled by default.

## 9. Smoke Tests

Smoke checks should verify:

- `/health`
- `/api/protocols`
- `/api/demo/status`
- `/api/demo/scenarios`
- `/api/demo/seed`
- seeded demo report retrieval
- `/api/analyze`
- report creation
- report retrieval
- Markdown export
- monitoring run
- discovered item retrieval
- evaluation run
- simulation run
- watchlist rule evaluation
- options analysis

After Phase 10, add a smoke path for approved-item ingest using a fixture or mocked discovered item.

After Phase 11, smoke checks can be extended with `AUTH_ENABLED=true` fixtures for admin/common authorization boundaries.

After Phase 12, add mocked lifecycle smoke tests only; do not rent a real Vast.ai instance in CI.

After Phase 13, smoke checks seed deterministic local demo records and retrieve one example report. The smoke path must not require paid APIs, external secrets, wallet access, or real Vast.ai rental.

## 10. Final Phase 13 Demo Tests

Demo tests should validate:

- demo seed works when `AUTH_ENABLED=false`
- demo seed requires admin when `AUTH_ENABLED=true`
- seed operation is idempotent
- records are clearly marked as synthetic demo data
- seeded reports can be retrieved through the normal report endpoint
- example Markdown reports can be generated from deterministic data
- no external API keys, wallet state, or real Vast.ai rental are required

## 11. Final Portfolio Test Pass

Before public deployment:

- backend tests pass
- frontend lint/build pass
- Docker config checks pass
- RAG eval passes
- no test requires live wallet, private key, or trade execution
- demo data is synthetic or read-only
- public environment has no admin secret exposed to frontend
