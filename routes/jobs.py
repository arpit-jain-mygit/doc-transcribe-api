from fastapi import APIRouter, HTTPException
from services.redis_client import redis_client
from services.queue import enqueue_job
import uuid
from datetime import datetime

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("/ocr")
def submit_ocr(payload: dict):
    job_id = f"ocr-{uuid.uuid4().hex}"

    redis_client.hset(
        f"job_status:{job_id}",
        mapping={
            "job_id": job_id,
            "status": "QUEUED",
            "created_at": datetime.utcnow().isoformat(),
        },
    )

    enqueue_job(
        {
            "job_id": job_id,
            "job_type": "OCR",
            "input_type": "PDF",
            **payload,
        }
    )

    return {"job_id": job_id, "status": "QUEUED"}


@router.post("/{job_id}/cancel")
def cancel_job(job_id: str):
    if not redis_client.exists(f"job_status:{job_id}"):
        raise HTTPException(404, "Job not found")

    redis_client.hset(
        f"job_status:{job_id}",
        mapping={
            "cancelled": "true",
            "updated_at": datetime.utcnow().isoformat(),
        },
    )

    return {"job_id": job_id, "status": "CANCEL_REQUESTED"}
