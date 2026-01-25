from fastapi import APIRouter, HTTPException
from uuid import uuid4
from datetime import datetime
from typing import Dict

from services.redis_client import redis_client
from services.queue import enqueue_job

router = APIRouter()


# ---------------------------------------------------------
# Utils
# ---------------------------------------------------------
def now() -> str:
    return datetime.utcnow().isoformat() + "Z"


def get_job_or_404(job_id: str) -> Dict:
    key = f"job_status:{job_id}"
    job = redis_client.hgetall(key)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


# ---------------------------------------------------------
# Submit OCR Job
# ---------------------------------------------------------
@router.post("/jobs/ocr")
def submit_ocr_job(payload: Dict):
    if "local_path" not in payload:
        raise HTTPException(status_code=400, detail="local_path is required")

    job_id = f"ocr-{uuid4().hex}"

    job = {
        "job_id": job_id,
        "job_type": "OCR",
        "input_type": "PDF",
        "local_path": payload["local_path"],
        "status": "QUEUED",
        "attempts": 0,
        "created_at": now(),
        "updated_at": now(),
    }

    redis_client.hset(f"job_status:{job_id}", mapping=job)
    enqueue_job(job)

    return {
        "job_id": job_id,
        "status": "QUEUED",
    }


# ---------------------------------------------------------
# Submit Transcription Job
# ---------------------------------------------------------
@router.post("/jobs/transcribe")
def submit_transcription_job(payload: Dict):
    if "url" not in payload:
        raise HTTPException(status_code=400, detail="url is required")

    job_id = f"transcribe-{uuid4().hex}"

    job = {
        "job_id": job_id,
        "job_type": "TRANSCRIPTION",
        "input_type": "VIDEO",
        "url": payload["url"],
        "status": "QUEUED",
        "attempts": 0,
        "created_at": now(),
        "updated_at": now(),
    }

    redis_client.hset(f"job_status:{job_id}", mapping=job)
    enqueue_job(job)

    return {
        "job_id": job_id,
        "status": "QUEUED",
    }


# ---------------------------------------------------------
# Get Job Status
# ---------------------------------------------------------
@router.get("/jobs/{job_id}")
def get_job_status(job_id: str):
    return get_job_or_404(job_id)


# ---------------------------------------------------------
# Retry Job (creates a NEW job)
# ---------------------------------------------------------
@router.post("/jobs/{job_id}/retry")
def retry_job(job_id: str):
    old_job = get_job_or_404(job_id)

    job_type = old_job.get("job_type")
    input_type = old_job.get("input_type")

    if not job_type or not input_type:
        raise HTTPException(status_code=400, detail="Invalid job state")

    prefix = job_type.lower()
    new_job_id = f"{prefix}-{uuid4().hex}"

    new_job = {
        "job_id": new_job_id,
        "job_type": job_type,
        "input_type": input_type,
        "status": "QUEUED",
        "attempts": 0,
        "created_at": now(),
        "updated_at": now(),
    }

    # carry original inputs
    if "local_path" in old_job:
        new_job["local_path"] = old_job["local_path"]

    if "url" in old_job:
        new_job["url"] = old_job["url"]

    redis_client.hset(f"job_status:{new_job_id}", mapping=new_job)
    enqueue_job(new_job)

    return {
        "new_job_id": new_job_id,
        "status": "QUEUED",
    }
