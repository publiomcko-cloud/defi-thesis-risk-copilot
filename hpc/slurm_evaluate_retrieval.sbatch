#!/bin/bash
#SBATCH --job-name=defi-rag-eval
#SBATCH --output=hpc/logs/%x-%j.out
#SBATCH --error=hpc/logs/%x-%j.err
#SBATCH --time=00:20:00
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G

set -euo pipefail

REPO_ROOT="${REPO_ROOT:-$SLURM_SUBMIT_DIR}"
APPTAINER_IMAGE="${APPTAINER_IMAGE:-$REPO_ROOT/defi-risk-copilot.sif}"
RETRIEVER="${RETRIEVER:-hybrid_semantic}"
OUTPUT_PATH="${OUTPUT_PATH:-backend/retrieval_eval_results.json}"

cd "$REPO_ROOT"
mkdir -p hpc/logs

apptainer exec \
  --bind "$REPO_ROOT:/workspace/project" \
  "$APPTAINER_IMAGE" \
  bash -lc "cd /workspace/project/backend && python scripts/evaluate_retrieval.py --retriever '$RETRIEVER' --output '/workspace/project/$OUTPUT_PATH'"
