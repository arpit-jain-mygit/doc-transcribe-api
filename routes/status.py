from fastapi import APIRouter, HTTPException
import redis
import os

router = APIRouter()

REDIS_URL = os.environ["REDIS_URL"]
r = redis.from_url(REDIS_URL, decode_responses=True)

@router.get("/jobs/{job_id}")
def job_status(job_id: str):
    key = f"job_status:{job_id}"

    if not r.exists(key):
        raise HTTPException(404, "Job not found")

    data = r.hgetall(key)

    # normalize ints
    for k in ["progress", "eta_sec", "current_page", "total_pages"]:
        if k in data and data[k] is not None:
            data[k] = int(data[k])

    return {
        "job_id": job_id,
        **data,
    }
