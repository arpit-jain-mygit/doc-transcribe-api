import os
import redis
from fastapi import APIRouter, HTTPException

from services.gcs import generate_signed_url

router = APIRouter()

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
r = redis.Redis.from_url(REDIS_URL, decode_responses=True)


@router.get("/status/{job_id}")
def get_status(job_id: str):
    key = f"job_status:{job_id}"
    data = r.hgetall(key)

    if not data:
        raise HTTPException(status_code=404, detail="Job not found")

    # --------------------------------------------------
    # 🔑 CONVERT gs:// → HTTPS SIGNED URL
    # --------------------------------------------------
    output_path = data.get("output_path")

    if output_path and output_path.startswith("gs://"):
        path = output_path.replace("gs://", "")
        bucket, blob = path.split("/", 1)

        signed_url = generate_signed_url(
            bucket_name=bucket,
            blob_path=blob,
            expiration_minutes=60,
        )

        data["output_path"] = signed_url

    return data
