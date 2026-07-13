# HPC and SLURM Readiness

These files are optional examples for running batch RAG and ML-preparation jobs on an HPC cluster.

They do not affect local Docker Compose, the FastAPI backend, the Next.js frontend, or normal development workflows.

## Files

```text
hpc/
  slurm_generate_embeddings.sbatch
  slurm_evaluate_retrieval.sbatch
  slurm_train_risk_classifier.sbatch
  apptainer.def
  README.md
```

## Assumptions

- The repository is available on a shared filesystem.
- Jobs run from the repository root.
- Python dependencies are installed in the Apptainer image or a cluster-provided environment.
- `DATABASE_URL` is set only for jobs that need persisted reports.
- Generated artifacts are written to local ignored paths or an HPC output directory.

## Build Apptainer Image

Example:

```bash
apptainer build defi-risk-copilot.sif hpc/apptainer.def
```

Some clusters require:

```bash
apptainer build --fakeroot defi-risk-copilot.sif hpc/apptainer.def
```

## Submit Jobs

From the repository root:

```bash
sbatch hpc/slurm_generate_embeddings.sbatch
sbatch hpc/slurm_evaluate_retrieval.sbatch
sbatch hpc/slurm_train_risk_classifier.sbatch
```

## Guardrails

- These jobs do not connect wallets.
- These jobs do not execute trades.
- These jobs do not change production risk scoring.
- The ML export job creates candidate examples only; labels are deterministic-rule labels, not human ground truth.
- Future fine-tuning must use reviewed and curated labels.
