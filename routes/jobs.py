# routes/jobs.py
import os
import redis
from fastapi import APIRouter, Depends

from services.auth import verify_google_token
from services.gcs import generate_signed_url

router = APIRouter()

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
r = redis.Redis.from_url(REDIS_URL, decode_responses=True)


@router.get("/jobs")
def list_jobs(user=Depends(verify_google_token)):
    email = user["email"].lower()
    job_ids = r.lrange(f"user_jobs:{email}", 0, -1)

    jobs = []

    for job_id in job_ids:
        data = r.hgetall(f"job_status:{job_id}")
        if not data:
            continue

        output_path = data.get("output_path")
        if output_path and output_path.startswith("gs://"):
            path = output_path.replace("gs://", "")
            bucket, blob = path.split("/", 1)

            data["output_path"] = generate_signed_url(
                bucket_name=bucket,
                blob_path=blob,
                expiration_minutes=60,
            )

        data["job_id"] = job_id
        jobs.append(data)

    return jobs
