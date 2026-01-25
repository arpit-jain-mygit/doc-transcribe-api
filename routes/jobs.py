from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from services.redis_client import redis_client
from services.queue import enqueue_job
import uuid
from datetime import datetime
import os

router = APIRouter(prefix="/jobs", tags=["jobs"])

# =====================================================
# CONFIG
# =====================================================
OUTPUT_DIRS = [
    "output_texts",   # OCR outputs
    "transcripts",    # Transcription outputs
]

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

# =====================================================
# DOWNLOAD OUTPUT (✅ FIX)
# =====================================================
@router.get("/download/{filename}")
def download_output(filename: str):
    """
    Download OCR or Transcription output file
    """

    for base_dir in OUTPUT_DIRS:
        file_path = os.path.join(base_dir, filename)

        if os.path.exists(file_path):
            return FileResponse(
                path=file_path,
                media_type="text/plain",
                filename=filename,
            )

    raise HTTPException(status_code=404, detail="File not found")
