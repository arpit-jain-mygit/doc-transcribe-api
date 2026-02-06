# routes/upload.py
import os
import uuid
import json
import redis
from datetime import datetime

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends

from services.gcs import upload_file
from services.auth import verify_google_token
from services.queue import enqueue_job

from utils.jobs import create_job_id
from auth import verify_token
from pydantic import BaseModel

router = APIRouter()

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
r = redis.Redis.from_url(REDIS_URL, decode_responses=True)

QUEUE_NAME = "doc_jobs"


def log(msg: str):
    print(f"[UPLOAD {datetime.utcnow().isoformat()}] {msg}", flush=True)


@router.post("/upload")
async def upload(
    file: UploadFile = File(...),
    type: str = Form(...),
    user=Depends(verify_google_token),
):
    if type not in ("OCR", "TRANSCRIPTION"):
        raise HTTPException(status_code=400, detail="Invalid job type")

    job_id = uuid.uuid4().hex
    email = user["email"].lower()

    log(f"User={email} Job={job_id}")

    # Upload input to GCS (stream-safe)
    gcs = upload_file(
        file_obj=file.file,
        destination_path=f"jobs/{job_id}/input/{file.filename}",
    )

    # Job status
    r.hset(
        f"job_status:{job_id}",
        mapping={
            "status": "QUEUED",
            "stage": "Queued",
            "progress": 0,
            "user": email,
            "job_type": type,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        },
    )

    # 🔑 USER → JOB INDEX (NEW)
    r.lpush(f"user_jobs:{email}", job_id)

    payload = {
        "job_id": job_id,
        "job_type": type,
        "input_gcs_uri": gcs["gcs_uri"],
        "filename": file.filename,
    }

    r.rpush(QUEUE_NAME, json.dumps(payload))

    return {"job_id": job_id}

class YoutubeRequest(BaseModel):
    url: str
    type: str = "TRANSCRIPTION"


@router.post("/youtube")
async def submit_youtube(
    payload: YoutubeRequest,
    user=Depends(verify_google_token),  # 🔑 SAME AS /upload
):
    job_id = create_job_id()
    email = user["email"].lower()

    log(f"YouTube job submit user={email} job_id={job_id}")

    # -------------------------------------------------
    # 1. CREATE INITIAL JOB STATUS (CRITICAL)
    # -------------------------------------------------
    r.hset(
        f"job_status:{job_id}",
        mapping={
            "status": "QUEUED",
            "stage": "Queued",
            "progress": 0,
            "user": email,              # 🔑 REQUIRED FOR /status
            "job_type": payload.type,
            "source": "youtube",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        },
    )

    # -------------------------------------------------
    # 2. USER → JOB INDEX (CONSISTENT WITH /upload)
    # -------------------------------------------------
    r.lpush(f"user_jobs:{email}", job_id)

    # -------------------------------------------------
    # 3. ENQUEUE WORKER PAYLOAD
    # -------------------------------------------------
    job = {
        "job_id": job_id,
        "source": "youtube",
        "url": payload.url,
        "type": payload.type,
        "email": email,               # 🔑 PROPAGATES OWNERSHIP
    }

    enqueue_job(job_id, job)

    return {"job_id": job_id}
