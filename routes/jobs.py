import json
import uuid
from datetime import datetime
from fastapi import APIRouter

from schemas.requests import OCRJobRequest, TranscriptionJobRequest
from schemas.responses import JobCreatedResponse
from services.redis_client import redis_client
from config import QUEUE_NAME

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("/ocr", response_model=JobCreatedResponse)
def create_ocr_job(req: OCRJobRequest):
    job_id = f"ocr-{uuid.uuid4().hex}"

    job = {
        "job_id": job_id,
        "job_type": "OCR",
        "input_type": "PDF",
        "local_path": req.local_path,
        "created_at": datetime.utcnow().isoformat() + "Z",
    }

    redis_client.lpush(QUEUE_NAME, json.dumps(job))

    return JobCreatedResponse(job_id=job_id)


@router.post("/transcription", response_model=JobCreatedResponse)
def create_transcription_job(req: TranscriptionJobRequest):
    job_id = f"tr-{uuid.uuid4().hex}"

    job = {
        "job_id": job_id,
        "job_type": "TRANSCRIPTION",
        "input_type": "VIDEO",
        "url": str(req.url),
        "created_at": datetime.utcnow().isoformat() + "Z",
    }

    redis_client.lpush(QUEUE_NAME, json.dumps(job))

    return JobCreatedResponse(job_id=job_id)
