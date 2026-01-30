from fastapi import APIRouter, HTTPException
import redis

router = APIRouter()
r = redis.Redis(host="REDIS_HOST", port=6379, decode_responses=True)

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
