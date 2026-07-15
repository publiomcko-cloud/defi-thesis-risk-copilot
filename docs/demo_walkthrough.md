# Demo Walkthrough

This walkthrough is for a local or hosted synthetic portfolio demo. It does not connect wallets, request keys, sign transactions, execute trades, provide buy/sell instructions, or rent real Vast.ai infrastructure.

## 1. Start the Stack

```bash
docker compose up -d --build
curl http://127.0.0.1:8000/health
```

Open:

```text
Frontend: http://127.0.0.1:3000
Demo dashboard: http://127.0.0.1:3000/demo
API docs: http://127.0.0.1:8000/docs
```

## 2. Seed Demo Data

Use either option:

```bash
backend/.venv/bin/python backend/scripts/seed_demo_data.py
```

```bash
curl -X POST http://127.0.0.1:8000/api/demo/seed
```

The seed operation is idempotent and writes synthetic data into existing persistence tables.

## 3. Review the Main Report

Open:

```text
http://127.0.0.1:3000/reports/demo_report_pendle_pt_loop
```

What to show:

- deterministic risk rating
- assumptions and missing data
- source references
- stress and monitoring sections
- non-advisory disclaimer

## 4. Walk Through Demo Scenarios

Use `/demo` to open:

- Pendle PT + lending loop report
- discovery-to-review-to-RAG example through `/review`
- watchlist alert example through `/watchlist`
- options/volatility workflow through `/options`
- Vast.ai dry-run admin page through `/admin/vast`

The Vast.ai demo record is dry-run metadata only. It does not rent a real remote GPU.

## 5. Inspect Example Markdown Reports

Example reports live in:

```text
examples/reports/
```

Included files:

- `pendle_pt_loop_report.md`
- `discovery_to_rag_report.md`
- `watchlist_alert_report.md`
- `options_volatility_report.md`
- `vast_dry_run_report.md`

## 6. Safety Notes

- All demo values are synthetic.
- Reports are educational research artifacts.
- Deterministic risk scoring remains the source of truth.
- LLM wording, if enabled elsewhere, cannot override deterministic fields.
- No wallet, custody, trading, or personalized financial advice is implemented.

## 7. Hosted Public Demo

For a hosted portfolio demo, use:

```env
PUBLIC_DEMO_MODE=true
LLM_SYNTHESIS_ENABLED=false
LLM_PROVIDER=disabled
VAST_ENABLED=false
VAST_DRY_RUN=true
RAG_SEMANTIC_ENABLED=false
```

Check:

```text
https://<your-render-service>.onrender.com/health
https://<your-render-service>.onrender.com/api/deployment/status
https://<your-vercel-app>.vercel.app/demo
```

Then seed the hosted demo:

```bash
curl -X POST https://<your-render-service>.onrender.com/api/demo/seed
```

Hosted mode uses the committed example Markdown files and persisted database records. It does not rely on durable runtime filesystem writes.
