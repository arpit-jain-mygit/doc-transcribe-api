# routes/jobs.py
import os
import redis
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException

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
            filename = data.get("output_filename") or os.path.basename(blob) or "transcript.txt"

            signed_url = generate_signed_url(
                bucket_name=bucket,
                blob_path=blob,
                expiration_minutes=60,
                download_filename=filename,
            )

            data["output_path"] = signed_url
            data["download_url"] = signed_url

        data["job_id"] = job_id
        jobs.append(data)

    return jobs


@router.post("/jobs/{job_id}/cancel")
def cancel_job(job_id: str, user=Depends(verify_google_token)):
    key = f"job_status:{job_id}"
    data = r.hgetall(key)

    if not data:
        raise HTTPException(status_code=404, detail="Job not found")

    if data.get("user") != user["email"].lower():
        raise HTTPException(status_code=403, detail="Forbidden")

    status = (data.get("status") or "").upper()
    if status in {"COMPLETED", "FAILED", "CANCELLED"}:
        return {
            "job_id": job_id,
            "status": status,
            "message": "Job already finished",
        }

    r.hset(
        key,
        mapping={
            "cancel_requested": "1",
            "status": "CANCELLED",
            "stage": "Cancelled by user",
            "updated_at": datetime.utcnow().isoformat(),
        },
    )

    return {
        "job_id": job_id,
        "status": "CANCELLED",
        "message": "Cancellation requested",
    }
