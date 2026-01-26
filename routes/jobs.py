from fastapi import APIRouter, HTTPException
from services.redis_client import redis_client
from services.queue import enqueue_job
import uuid
from datetime import datetime

router = APIRouter(prefix="/jobs", tags=["jobs"])


# =====================================================
# OCR SUBMISSION
# =====================================================
@router.post("/ocr")
def submit_ocr(payload: dict):
    job_id = f"ocr-{uuid.uuid4().hex}"

    redis_client.hset(
        f"job_status:{job_id}",
        mapping={
            "job_id": job_id,
            "job_type": "OCR",
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

# =====================================================
# TRANSCRIPTION SUBMISSION
# =====================================================
@router.post("/transcription")
def submit_transcription(payload: dict):
    """
    payload:
      {
        "url": "https://youtube.com/..."
      }
    """

    job_id = f"transcribe-{uuid.uuid4().hex}"

    redis_client.hset(
        f"job_status:{job_id}",
        mapping={
            "job_id": job_id,
            "job_type": "TRANSCRIBE",
            "status": "QUEUED",
            "created_at": datetime.utcnow().isoformat(),
        },
    )

    enqueue_job(
        {
            "job_id": job_id,
            "job_type": "TRANSCRIBE",
            "input_type": "YOUTUBE",
            **payload,
        }
    )

    return {"job_id": job_id, "status": "QUEUED"}

# =====================================================
# CANCEL JOB
# =====================================================
@router.post("/{job_id}/cancel")
def cancel_job(job_id: str):
    if not redis_client.exists(f"job_status:{job_id}"):
        raise HTTPException(status_code=404, detail="Job not found")

    redis_client.hset(
        f"job_status:{job_id}",
        mapping={
            "cancelled": "true",
            "updated_at": datetime.utcnow().isoformat(),
        },
    )

    return {"job_id": job_id, "status": "CANCEL_REQUESTED"}
