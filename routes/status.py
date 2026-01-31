import os
import redis
from fastapi import APIRouter, HTTPException
from worker.utils.gcs import generate_signed_url

router = APIRouter()

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
r = redis.Redis.from_url(REDIS_URL, decode_responses=True)


@router.get("/status/{job_id}")
def get_status(job_id: str):
    key = f"job_status:{job_id}"
    data = r.hgetall(key)

    if not data:
        raise HTTPException(status_code=404, detail="Job not found")

    # ✅ CREATE DOWNLOAD URL ONLY WHEN READY
    if data.get("status") == "COMPLETED":
        bucket = data.get("output_bucket")
        blob = data.get("output_blob")

        if bucket and blob:
            data["output_path"] = generate_signed_url(
                bucket_name=bucket,
                blob_path=blob,
                expiration_minutes=60,
            )

    return data
