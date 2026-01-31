# routes/upload.py

import os
import uuid
import json
import shutil
from datetime import datetime

import redis
from fastapi import APIRouter, UploadFile, File, Form, HTTPException

from services.gcs import upload_file_to_gcs  # ✅ EXACT FUNCTION

router = APIRouter()

# ---------------------------------------------------------
# CONFIG
# ---------------------------------------------------------
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
UPLOAD_DIR = "uploads"
QUEUE_NAME = "doc_jobs"

os.makedirs(UPLOAD_DIR, exist_ok=True)

r = redis.Redis.from_url(REDIS_URL, decode_responses=True)

# ---------------------------------------------------------
# UPLOAD
# ---------------------------------------------------------
@router.post("/upload")
async def upload(
    file: UploadFile = File(...),
    type: str = Form(...),  # OCR | TRANSCRIPTION
):
    if type not in {"OCR", "TRANSCRIPTION"}:
        raise HTTPException(status_code=400, detail="Invalid job type")

    job_id = uuid.uuid4().hex
    filename = f"{job_id}_{file.filename}"
    local_path = os.path.join(UPLOAD_DIR, filename)

    # -----------------------------------------------------
    # SAVE FILE LOCALLY (FOR WORKER)
    # -----------------------------------------------------
    with open(local_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # -----------------------------------------------------
    # UPLOAD INPUT TO GCS (STREAM MODE)
    # -----------------------------------------------------
    with open(local_path, "rb") as f:
        gcs_uri = upload_file_to_gcs(
            file_obj=f,
            object_name=f"jobs/{job_id}/input/{file.filename}",
        )

    # -----------------------------------------------------
    # INIT REDIS STATUS
    # -----------------------------------------------------
    r.hset(
        f"job_status:{job_id}",
        mapping={
            "status": "QUEUED",
            "progress": 0,
            "job_type": type,
            "input_path": local_path,     # 🔴 LOCAL FOR WORKER
            "input_gcs": gcs_uri,         # 🟢 GCS FOR REFERENCE
            "created_at": datetime.utcnow().isoformat(),
        },
    )

    # -----------------------------------------------------
    # PUSH JOB TO QUEUE (JSON, NOT repr)
    # -----------------------------------------------------
    r.lpush(
        QUEUE_NAME,
        json.dumps({
            "job_id": job_id,
            "job_type": type,
            "input_path": local_path,
        }),
    )

    return {"job_id": job_id}
