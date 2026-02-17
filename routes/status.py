# User value: This file helps users get reliable OCR/transcription results with clear processing behavior.
# routes/status.py
import os
import redis
from fastapi import APIRouter, HTTPException, Depends

from services.auth import verify_google_token
from services.gcs import generate_signed_url
from utils.request_id import get_request_id
from utils.stage_logging import log_stage

router = APIRouter()

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
r = redis.Redis.from_url(REDIS_URL, decode_responses=True)


# User value: normalizes data so users see consistent OCR/transcription results.
def normalize_failure_fields(data: dict) -> None:
    status = (data.get("status") or "").upper()
    if status != "FAILED":
        return

    error_code = str(data.get("error_code") or "").strip().upper()
    if not error_code:
        data["error_code"] = "PROCESSING_FAILED"

    error_message = str(data.get("error_message") or "").strip()
    if not error_message:
        fallback = str(data.get("error") or data.get("stage") or "Processing failed. Please try again.").strip()
        data["error_message"] = fallback


@router.get("/status/{job_id}")
# User value: loads latest OCR/transcription data so users see current status.
def get_status(
    job_id: str,
    user=Depends(verify_google_token),
):
    email = user["email"].lower()
    log_stage(job_id=job_id, stage="STATUS_READ", event="STARTED", user=email)

    key = f"job_status:{job_id}"
    data = r.hgetall(key)

    if not data:
        log_stage(job_id=job_id, stage="STATUS_READ", event="FAILED", user=email, error="Job not found")
        raise HTTPException(status_code=404, detail="Job not found")

    if data.get("user") != email:
        log_stage(job_id=job_id, stage="STATUS_READ", event="FAILED", user=email, error="Forbidden")
        raise HTTPException(status_code=403, detail="Forbidden")

    if not data.get("request_id"):
        rid = get_request_id()
        if rid:
            data["request_id"] = rid

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

        data["download_url"] = signed_url

    normalize_failure_fields(data)

    log_stage(
        job_id=job_id,
        stage="STATUS_READ",
        event="COMPLETED",
        user=email,
        job_type=data.get("job_type"),
        source=data.get("source"),
        status=data.get("status"),
        worker_stage=data.get("stage"),
        progress=data.get("progress"),
        error_code=data.get("error_code"),
    )

    return data
