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

    return {
        "job_id": job_id,
        "status": data.get("status", ""),
        "stage": data.get("stage", ""),
        "progress": int(data.get("progress") or 0),
        "eta_sec": int(data.get("eta_sec") or 0),
        "current_page": int(data.get("current_page") or 0),
        "total_pages": int(data.get("total_pages") or 0),
        "output_uri": data.get("output_uri") or "",
        "error": data.get("error") or "",
    }
