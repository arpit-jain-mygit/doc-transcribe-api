# User value: This file helps users get reliable OCR/transcription results with clear processing behavior.
from datetime import datetime
from typing import Dict

# Simple in-memory store (replace with Redis later)
JOBS: Dict[str, dict] = {}

# User value: builds the required payload/state for user OCR/transcription flow.
def create_job(job_id: str, gcs_uri: str) -> dict:
    job = {
        "job_id": job_id,
        "status": "queued",
        "progress": 0,
        "input_gcs_uri": gcs_uri,
        "created_at": datetime.utcnow().isoformat() + "Z",
    }
    JOBS[job_id] = job
    return job

# User value: loads latest OCR/transcription data so users see current status.
def get_job(job_id: str) -> dict | None:
    return JOBS.get(job_id)
