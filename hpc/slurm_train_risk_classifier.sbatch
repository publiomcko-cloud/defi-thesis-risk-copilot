#!/bin/bash
#SBATCH --job-name=defi-risk-export
#SBATCH --output=hpc/logs/%x-%j.out
#SBATCH --error=hpc/logs/%x-%j.err
#SBATCH --time=00:30:00
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G

set -euo pipefail

REPO_ROOT="${REPO_ROOT:-$SLURM_SUBMIT_DIR}"
APPTAINER_IMAGE="${APPTAINER_IMAGE:-$REPO_ROOT/defi-risk-copilot.sif}"
OUTPUT_PATH="${OUTPUT_PATH:-model-training/datasets/risk_training_examples.json}"

cd "$REPO_ROOT"
mkdir -p hpc/logs model-training/datasets

apptainer exec \
  --bind "$REPO_ROOT:/workspace/project" \
  "$APPTAINER_IMAGE" \
  bash -lc "cd /workspace/project/backend && python scripts/export_training_dataset.py --output '/workspace/project/$OUTPUT_PATH'"
