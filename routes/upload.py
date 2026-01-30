import os
import uuid
import json
import redis
import shutil
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, Form, HTTPException

router = APIRouter()

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")

os.makedirs(UPLOAD_DIR, exist_ok=True)
UPLOAD_DIR = os.path.abspath(UPLOAD_DIR)  # ✅ ABSOLUTE PATH

r = redis.Redis.from_url(REDIS_URL, decode_responses=True)


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    type: str = Form(...)
):
    if type not in ("OCR", "TRANSCRIPTION"):
        raise HTTPException(status_code=400, detail="Invalid job type")

    job_id = uuid.uuid4().hex
    filename = f"{job_id}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, filename)

    with open(file_path, "wb") as out:
        shutil.copyfileobj(file.file, out)

    # ✅ create QUEUED status
    r.hset(
        f"job_status:{job_id}",
        mapping={
            "status": "QUEUED",
            "progress": 0,
            "eta_sec": 0,
            "updated_at": datetime.utcnow().isoformat(),
        },
    )

    job = {
        "job_id": job_id,
        "job_type": "OCR" if type == "OCR" else "TRANSCRIBE",
        "input_path": file_path,   # ✅ ABSOLUTE
    }

    r.rpush("doc_jobs", json.dumps(job))

    return {"job_id": job_id}
