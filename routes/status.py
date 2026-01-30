from fastapi import APIRouter, HTTPException
import redis
import os

router = APIRouter()
REDIS_URL = os.environ.get("REDIS_URL")
if not REDIS_URL:
    raise RuntimeError("REDIS_URL env var not set")

r = redis.from_url(REDIS_URL, decode_responses=True)

@router.get("/jobs/{job_id}")
def job_status(job_id: str):
    key = f"job:{job_id}"
    if not r.exists(key):
        raise HTTPException(404, "Job not found")

    return {
        "job_id": job_id,
        "status": r.hget(key, "status"),
        "progress": int(r.hget(key, "progress")),
        "output_uri": r.hget(key, "output_uri"),
        "error": r.hget(key, "error"),
    }
