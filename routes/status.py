# routes/status.py
import os
import redis
from fastapi import APIRouter, HTTPException, Depends

from services.auth import verify_google_token
from services.gcs import generate_signed_url

router = APIRouter()

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
r = redis.Redis.from_url(REDIS_URL, decode_responses=True)


@router.get("/status/{job_id}")
def get_status(
    job_id: str,
    user=Depends(verify_google_token),
):
    key = f"job_status:{job_id}"
    data = r.hgetall(key)

    if not data:
        raise HTTPException(status_code=404, detail="Job not found")

    if data.get("user") != user["email"]:
        raise HTTPException(status_code=403, detail="Forbidden")

    output_path = data.get("output_path")

    if output_path and output_path.startswith("gs://"):
        path = output_path.replace("gs://", "")
        bucket, blob = path.split("/", 1)

        data["output_path"] = generate_signed_url(
            bucket_name=bucket,
            blob_path=blob,
            expires_days=1,
        )

    return data
