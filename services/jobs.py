# User value: This file helps users get reliable OCR/transcription results with clear processing behavior.
from datetime import datetime
from typing import Dict

# Simple in-memory store (replace with Redis later)
JOBS: Dict[str, dict] = {}

# User value: This step keeps the user OCR/transcription flow accurate and dependable.
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

# User value: This step keeps the user OCR/transcription flow accurate and dependable.
def get_job(job_id: str) -> dict | None:
    return JOBS.get(job_id)
