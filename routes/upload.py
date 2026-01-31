import os
import uuid
import json
import redis
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Header
from datetime import datetime

from services.gcs import upload_file

def log(msg: str):
    print(f"[TRANSCRIBE {datetime.utcnow().isoformat()}] {msg}", flush=True)

router = APIRouter()

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
r = redis.Redis.from_url(REDIS_URL, decode_responses=True)

QUEUE_NAME = "doc_jobs"


@router.post("/upload")
async def upload(
    file: UploadFile = File(...),
    type: str = Form(...),
    authorization: str = Header(None),   # ✅ ADD
):
    # --------------------------------------------------
    # AUTH CHECK (TEMP – presence only)
    # --------------------------------------------------
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    # OPTIONAL: strip Bearer
    token = authorization.replace("Bearer ", "").strip()
    if not token:
        raise HTTPException(status_code=401, detail="Invalid Authorization token")

    # --------------------------------------------------
    # EXISTING LOGIC (UNCHANGED)
    # --------------------------------------------------
    if type not in ("OCR", "TRANSCRIPTION"):
        raise HTTPException(status_code=400, detail="Invalid job type")

    job_id = uuid.uuid4().hex

    # Upload input file to GCS
    gcs = upload_file(
        file_obj=file.file,
        destination_path=f"jobs/{job_id}/input/{file.filename}",
    )

    log("About to enqueue Redis job")

    r.hset(
        f"job_status:{job_id}",
        mapping={
            "status": "QUEUED",
            "progress": 0,
            "updated_at": "",
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
