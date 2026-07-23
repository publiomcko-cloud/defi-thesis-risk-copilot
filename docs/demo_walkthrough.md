# Demo Walkthrough

The demo uses synthetic educational data. It does not connect wallets, request keys, sign transactions, execute trades, provide buy/sell instructions, or rent real Vast.ai infrastructure.

## 1. Hosted Demo

Open:

- Guided demo: `https://defi-thesis-risk-copilot.vercel.app/demo`
- Main report: `https://defi-thesis-risk-copilot.vercel.app/reports/demo_report_pendle_pt_loop`
- Backend readiness: `https://defi-thesis-risk-copilot.onrender.com/ready`
- API docs: `https://defi-thesis-risk-copilot.onrender.com/docs`

The Render free tier may need a short cold start. The demo page and report page expose retry/readiness actions.

The hosted backend seeds deterministic data and builds the curated RAG index during startup. The public `/api/demo/seed` endpoint is blocked intentionally.

## 2. Recommended Review Sequence

### Step 1 — Product overview

Open the homepage and note:

- the research-not-trading boundary
- deterministic risk scoring
- controlled knowledge workflow
- hosted Vercel/Render/Supabase architecture

### Step 2 — Guided demo dashboard

Open `/demo` and review:

- environment/database state
- demo record counts
- public read-only notice
- shared-database privacy warning
- guided scenario cards

### Step 3 — Main Pendle/Morpho report

Open the main report and inspect:

- executive summary
- deterministic risk rating
- assumptions
- missing data
- stress and monitoring sections
- clickable source references
- Markdown copy/download
- non-advisory disclaimer

### Step 4 — Strategy analysis

Open `/analyze`.

Use the provided synthetic example or another non-sensitive thesis. Percentage fields use normal user units:

```text
5 = 5%
50 = 50%
```

Do not submit wallet addresses, credentials, private positions, confidential information, or personally identifying data. Public reports use a shared demonstration database.

### Step 5 — Simulator

Open `/simulate` and show:

- core assumptions
- advanced stress controls
- borrow-rate shock
- liquidity/slippage shock
- collateral drawdown
- early-exit and combined adverse cases
- transparent calculation details

### Step 6 — Options analysis

Open `/options` and show:

- long call/put selection
- premium and contracts
- implied volatility in percentage units
- breakeven
- maximum loss
- bid/ask spread
- payoff scenarios
- educational volatility framing

### Step 7 — Read-only research workflow

Open `/review`.

The hosted page demonstrates:

- discovered candidates
- source provenance
- evaluation summaries
- risk/confidence metadata
- reviewer notes
- approved/ingested status

Public visitors cannot run discovery, create evaluations, change review status, or ingest content.

### Step 8 — Read-only watchlist

Open `/watchlist` and show:

- human-readable threshold rules
- current snapshot
- open alert metadata
- no trade execution or notification dependency

Public visitors cannot mutate shared watchlist/alert records.

### Step 9 — API and source review

Open:

- API docs
- backend readiness
- deployment status
- GitHub repository
- consolidated development plan

## 3. Local Demo

Start:

```bash
docker compose up -d --build
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/ready
```

Open:

```text
Frontend: http://127.0.0.1:3000
Demo: http://127.0.0.1:3000/demo
API docs: http://127.0.0.1:8000/docs
```

Seed manually when running a non-public local environment:

```bash
backend/.venv/bin/python backend/scripts/seed_demo_data.py
```

or:

```bash
curl -X POST http://127.0.0.1:8000/api/demo/seed
```

The seed is idempotent.

## 4. Example Reports

Committed Markdown examples:

```text
examples/reports/pendle_pt_loop_report.md
examples/reports/discovery_to_rag_report.md
examples/reports/watchlist_alert_report.md
examples/reports/options_volatility_report.md
examples/reports/vast_dry_run_report.md
```

## 5. Public Safety Checks

Expected public behavior:

```bash
curl https://defi-thesis-risk-copilot.onrender.com/ready
curl https://defi-thesis-risk-copilot.onrender.com/api/demo/status
curl https://defi-thesis-risk-copilot.onrender.com/api/reports/demo_report_pendle_pt_loop
```

Expected `403`:

```bash
curl -i -X POST https://defi-thesis-risk-copilot.onrender.com/api/demo/seed
curl -i -X POST https://defi-thesis-risk-copilot.onrender.com/api/monitoring/run \
  -H 'Content-Type: application/json' -d '{}'
curl -i -X POST https://defi-thesis-risk-copilot.onrender.com/api/discovery/run \
  -H 'Content-Type: application/json' -d '{}'
```

## 6. Safety Notes

- All seeded values are synthetic.
- Reports are research artifacts, not recommendations.
- Deterministic scoring remains authoritative.
- Optional model wording cannot override deterministic fields.
- Public privileged workflows are read-only.
- No wallet, custody, transaction signing, trade execution, or personalized financial advice is implemented.

## 7. Phase 16 Private Product Preview

Private deployments can enable:

- Supabase Auth login/signup/recovery
- private reports and watchlists
- saved theses
- organizations and memberships
- account export/deletion
- daily usage quotas

The public portfolio demo keeps privileged mutations blocked. Anonymous generated reports are isolated by server-generated HttpOnly anonymous-session cookies, while seeded demo reports remain globally readable.
