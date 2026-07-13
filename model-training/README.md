# Model Training Groundwork

This directory is for Post-MVP Phase 8 dataset exports and baseline ML experiments.

No model in this directory is authoritative for production risk scoring. The app's deterministic rule-based risk framework remains the source of truth for report risk ratings.

No trained production model is committed in this repository. Files generated under `datasets/` are reproducible local experiment artifacts, not production model assets.

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

- `risk_rating`: deterministic report risk rating, not human ground truth.
- `deterministic_risk_score`: rule-based score when present in report text.
- `main_risk_drivers`: inferred risk categories from report text and missing data.
- `protocol_category`: `unknown`, `single_protocol:<protocol>`, or `multi_protocol`.
- `missing_data_severity`: `none`, `low`, `medium`, or `high`.
- `strategy_type`: `lending`, `leveraged_lending`, `fixed_yield`, `options`, or `generic_defi`.
- `label_source`: `deterministic_rules` for current exports.
- `human_ground_truth`: `false` for current exports.

## Guardrails

- Do not fine-tune before enough reviewed examples exist.
- Future fine-tuning must use reviewed and curated labels, not raw deterministic exports alone.
- Do not use baseline classifier predictions to override deterministic scoring.
- Treat model output as advisory comparison data only.
- Keep missing data and uncertainty visible.
