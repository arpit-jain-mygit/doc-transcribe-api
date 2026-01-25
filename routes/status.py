from fastapi import APIRouter, HTTPException
from services.redis_client import redis_client
from schemas.responses import JobStatusResponse

router = APIRouter(prefix="/jobs", tags=["status"])


@router.get("/{job_id}", response_model=JobStatusResponse)
def get_job_status(job_id: str):
    key = f"job_status:{job_id}"
    data = redis_client.hgetall(key)

    if not data:
        raise HTTPException(status_code=404, detail="Job not found")

    data["job_id"] = job_id
    return data
