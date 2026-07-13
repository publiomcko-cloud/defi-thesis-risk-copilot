# Model Training Groundwork

This directory is for Post-MVP Phase 8 dataset exports and baseline ML experiments.

No model in this directory is authoritative for production risk scoring. The app's deterministic rule-based risk framework remains the source of truth for report risk ratings.

## Current Files

```text
datasets/
  risk_training_examples.json
```

Generate the dataset from persisted reports:

```bash
cd backend
source .venv/bin/activate
python scripts/export_training_dataset.py
```

## Label Schema

- `risk_rating`: deterministic report risk rating.
- `main_risk_drivers`: inferred risk categories from report text and missing data.
- `protocol_category`: `unknown`, `single_protocol:<protocol>`, or `multi_protocol`.
- `missing_data_severity`: `none`, `low`, `medium`, or `high`.
- `strategy_type`: `lending`, `leveraged_lending`, `fixed_yield`, `options`, or `generic_defi`.

## Guardrails

- Do not fine-tune before enough reviewed examples exist.
- Do not use baseline classifier predictions to override deterministic scoring.
- Treat model output as advisory comparison data only.
- Keep missing data and uncertainty visible.
