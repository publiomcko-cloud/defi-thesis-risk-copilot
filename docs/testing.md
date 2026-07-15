# Testing — DeFi Thesis & Risk Copilot

## 1. Testing Goals

Validation covers:

- API contracts and authorization
- deterministic risk-scoring behavior
- RAG retrieval and citation metadata
- report generation and persistence
- market-data fallbacks and cache expiration
- discovery, evaluation, review, and ingestion safety
- simulation and options calculations
- watchlist and alert rules
- credential isolation
- Vast.ai lifecycle guardrails
- public-demo mutation boundaries
- startup preparation and readiness
- frontend type/build quality
- Docker and deployment configuration

No automated test may require a wallet, private key, trade execution, paid model API, or real Vast.ai rental.

## 2. Baseline Validation

```bash
cd backend
source .venv/bin/activate
alembic upgrade head
python -m compileall app
python -m pytest -q
python scripts/run_smoke_checks.py

cd ../frontend
npm run lint
npm run build

cd ..
docker compose config
docker compose -f docker-compose.production.yml config
```

## 3. Public-Demo Security Tests

`backend/app/tests/test_public_demo_security.py` validates:

- unauthenticated public visitors receive a `common` identity
- public visitors do not receive an administrator identity
- credential metadata is not public
- public demo seeding is blocked
- monitoring runs are blocked
- document/RAG refresh mutations are blocked
- discovery runs are blocked
- evaluation creation is blocked
- watchlist mutations are blocked
- bounded compute remains available
- public compute rate limits return `429` and `Retry-After`

Additional existing deployment tests validate:

- provider credential mutations return `403`
- real Vast.ai startup returns `403`
- deployment metadata contains no URLs, passwords, keys, or secrets
- public runtime seed skips example-report filesystem writes

## 4. Input Validation Tests

Public request schemas enforce:

- strategy-description maximum length
- protocol-count maximum
- URL and text limits
- percentage/range limits
- scenario-count limits
- maximum document-content size
- unknown-field rejection where contracts should be strict

Tests should include both valid boundary values and rejected oversized payloads.

## 5. Runtime and Health Tests

The application exposes:

- `/health` for liveness
- `/ready` for database and RAG readiness
- `/api/deployment/status` for safe operational metadata

Tests should validate:

- root endpoint returns service links without secrets
- health works independently of database state
- readiness returns `503` when PostgreSQL is unavailable
- readiness returns `503` in public mode when the RAG index is absent
- readiness succeeds after runtime preparation
- public runtime preparation is idempotent
- local non-public runtime preparation does not unexpectedly seed data

## 6. PostgreSQL Integration

CI should run Alembic against PostgreSQL, not only SQLite.

Required path:

```text
PostgreSQL service
  -> alembic upgrade head
  -> runtime preparation in public-demo mode
  -> pytest
```

This catches:

- dialect differences
- migration-order failures
- timezone behavior
- JSON-column behavior
- pooler-compatible URL handling

## 7. RAG Validation

```bash
cd backend
python scripts/build_retrieval_eval_dataset.py
python scripts/evaluate_retrieval.py --retriever hybrid
python scripts/evaluate_retrieval.py --retriever hybrid_semantic
```

The retriever should:

- return protocol-relevant chunks
- preserve source metadata
- respect protocol filters
- keep citation fields intact
- retrieve approved ingested knowledge after a successful refresh

RAG ingestion tests cover:

- eligibility only for `approved_for_rag`
- explicit action requirement
- duplicate prevention
- Markdown provenance and disclaimer
- `refresh_pending`
- `refresh_failed`
- retry after refresh failure
- `ingested` only after successful refresh

## 8. Access Control and Credentials

Authentication tests cover:

```text
admin
common
public demo common identity
local auth-disabled demo admin
```

Credential tests verify:

- full secrets never return from the API
- full secrets never enter frontend payloads
- database secrets are encrypted
- missing encryption configuration fails closed
- audit metadata is redacted
- common users cannot manage credentials
- public users cannot read credential metadata
- disabled/rotated credentials are not reused

The bearer-token path is an MVP foundation. Managed-identity tests are planned for V1 Phase 16.

## 9. Discovery, Review, and RAG

Tests cover:

- collector normalization
- quality/TVL filters
- duplicate discovery prevention
- initial `needs_review` state
- optional automatic evaluation
- review-item creation
- allowed review states
- private/admin review mutations
- public read-only listing
- human approval before ingestion
- audit events for privileged actions

## 10. Market-Data Cache

Tests should verify:

- live data is normalized and cached
- repeated source/key writes update rather than append indefinitely
- duplicate historical rows are cleaned
- expired rows are not used
- unexpired cache is used after live failure
- unavailable state and missing fields are explicit without valid cache

## 11. Simulation and Options

Simulation tests cover:

- net spread
- borrow-rate shock
- liquidity/slippage shock
- collateral drawdown
- early exit
- incentive removal
- combined adverse scenario
- bounded numeric inputs

Options tests cover:

- call and put breakeven
- maximum loss
- payoff scenarios
- contracts
- spread calculation
- expiration calculation
- scenario-count bounds
- no buy/sell recommendation language

## 12. Vast.ai

Automated tests use fakes/dry-run only.

Coverage includes:

- disabled-provider error
- offer filters
- cost/runtime limits
- active-instance limit
- startup polling and timeout
- unsafe remote states
- test prompt through mocked OpenAI-compatible endpoint
- cleanup after failure
- idempotent destroy
- raw API-key isolation
- audit events
- common/public denial

## 13. ML and HPC Groundwork

ML validation:

```bash
cd backend
python scripts/export_training_dataset.py
```

Exported labels must be identified as deterministic-rule labels rather than human ground truth. Model output remains advisory.

HPC syntax validation:

```bash
bash -n hpc/slurm_generate_embeddings.sbatch
bash -n hpc/slurm_evaluate_retrieval.sbatch
bash -n hpc/slurm_train_risk_classifier.sbatch
test -f hpc/apptainer.def
```

## 14. Smoke Testing Modes

### Local/private smoke path

The existing smoke script can exercise mutations when:

```env
PUBLIC_DEMO_MODE=false
```

It may seed, run monitoring/discovery, update review state, create/evaluate watchlists, and run compute flows.

### Hosted public smoke path

A deployed smoke check should verify:

- root, health, readiness, and deployment status
- demo status/scenarios
- seeded report retrieval
- protocols
- simulation and options compute
- expected `403` for public mutations
- no secret-bearing fields

Do not run the local mutation smoke script unchanged against the public deployment.

## 15. Frontend Quality

Current frontend validation:

```bash
cd frontend
npm run lint
npm run build
```

The current `lint` script performs strict TypeScript compilation. Planned production additions:

- ESLint
- Playwright end-to-end tests
- axe accessibility checks
- visual regression checks
- mobile viewport tests
- cold-start retry tests
- public/private navigation tests

## 16. Phase 15 Completion Gate

Before merging V1 Phase 15:

- [ ] Alembic succeeds on PostgreSQL.
- [ ] Backend tests pass.
- [ ] Public-security tests pass.
- [ ] Frontend TypeScript check passes.
- [ ] Next.js build passes.
- [ ] Compose files validate.
- [ ] Vercel preview succeeds.
- [ ] Render deployment succeeds.
- [ ] `/ready` succeeds after startup.
- [ ] Public mutation probes return `403`.
- [ ] Main report, simulation, options, review, and watchlist pages render.
- [ ] No secret is exposed.
- [ ] Known limitations remain documented.
