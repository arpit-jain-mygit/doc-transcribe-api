import os
import uuid
import json
import redis
from datetime import datetime

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Header

from services.gcs import upload_file

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
    authorization: str = Header(None),
):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    if type not in ("OCR", "TRANSCRIPTION"):
        raise HTTPException(status_code=400, detail="Invalid job type")

    job_id = uuid.uuid4().hex

    log(f"Uploading input file for job {job_id}")

    gcs = upload_file(
        file_obj=file.file,
        destination_path=f"jobs/{job_id}/input/{file.filename}",
    )

    r.hset(
        f"job_status:{job_id}",
        mapping={
            "status": "QUEUED",
            "progress": 0,
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

    log(f"Job enqueued: {job_id}")

    return {"job_id": job_id}
