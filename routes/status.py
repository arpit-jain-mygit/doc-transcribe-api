import os
import redis
from fastapi import APIRouter, HTTPException

router = APIRouter()

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
r = redis.Redis.from_url(REDIS_URL, decode_responses=True)


@router.get("/status/{job_id}")
def get_status(job_id: str):
    key = f"job_status:{job_id}"
    data = r.hgetall(key)

    if not data:
        raise HTTPException(status_code=404, detail="Job not found")

    # FIX: normalize output field for UI
    # prefer output_uri (GCS), fallback to output_path (local)
    if "output_uri" in data:
        data["output_path"] = data["output_uri"]

    return data
