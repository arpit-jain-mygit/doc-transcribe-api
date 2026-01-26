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
    input_type = payload.get("input_type", "PDF")

    redis_client.hset(
        f"job_status:{job_id}",
        mapping={
            "job_id": job_id,
            "job_type": "OCR",
            "status": "QUEUED",
            "created_at": datetime.utcnow().isoformat(),
        },
    )

    job_payload = {
        "job_id": job_id,
        "job_type": "OCR",
        "input_type": input_type,
    }

    # ------------------------------------------
    # OPTION B: GitHub → GCS → OCR
    # ------------------------------------------
    if input_type == "GITHUB":
        github_url = payload.get("url")
        if not github_url:
            raise HTTPException(400, "Missing GitHub PDF URL")

        job_payload["github_url"] = github_url

    # ------------------------------------------
    # Local / direct PDF (existing flow)
    # ------------------------------------------
    else:
        job_payload.update(payload)

    enqueue_job(job_payload)

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
