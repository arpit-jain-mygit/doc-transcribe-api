# routes/upload.py
import os
import uuid
import json
import redis
from datetime import datetime

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends

from services.gcs import upload_file
from services.auth import verify_google_token

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
    log(f"User={user['email']} Job={job_id}")

    # Upload input file to GCS (stream-safe)
    gcs = upload_file(
        file_obj=file.file,
        destination_path=f"jobs/{job_id}/input/{file.filename}",
    )

    # Initial job status (NO APPROVAL CONCEPT)
    r.hset(
        f"job_status:{job_id}",
        mapping={
            "status": "QUEUED",
            "progress": 0,
            "user": user["email"],
            "updated_at": datetime.utcnow().isoformat(),
        },
    )

    payload = {
        "job_id": job_id,
        "job_type": type,
        "input_gcs_uri": gcs["gcs_uri"],
        "filename": file.filename,
    }

    r.rpush(QUEUE_NAME, json.dumps(payload))

    return {"job_id": job_id}
