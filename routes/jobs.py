from fastapi import APIRouter, HTTPException
from services.jobs import get_job

router = APIRouter(prefix="/jobs")

@router.get("/{job_id}")
def get_job_status(job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job
