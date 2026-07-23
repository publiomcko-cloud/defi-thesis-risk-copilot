from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.policies import has_org_role, READ_ORG_ROLES
from app.auth.schemas import UserContext
from app.models.job import JobModel


def get_visible_job(db: Session, actor: UserContext, job_id: str) -> JobModel:
    """Resolve a job without letting its identifier bypass Phase 16 ownership rules."""
    job = db.execute(
        select(JobModel).where(JobModel.id == job_id).where(JobModel.deleted_at.is_(None))
    ).scalars().one_or_none()
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.owner_user_id == actor.id:
        return job
    if job.visibility == "organization" and job.organization_id and has_org_role(
        db,
        actor.id,
        job.organization_id,
        READ_ORG_ROLES,
    ):
        return job
    raise HTTPException(status_code=404, detail="Job not found")
