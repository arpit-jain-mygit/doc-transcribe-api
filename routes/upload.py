# routes/upload.py
import os
import re
import uuid
import json
import redis
import logging
import unicodedata
from datetime import datetime

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends

from services.gcs import upload_file
from services.auth import verify_google_token

router = APIRouter()
logger = logging.getLogger("api.upload")

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
r = redis.Redis.from_url(REDIS_URL, decode_responses=True)

QUEUE_NAME = os.getenv("QUEUE_NAME", "doc_jobs")


def log(msg: str):
    print(f"[UPLOAD {datetime.utcnow().isoformat()}] {msg}", flush=True)
    logger.info(msg)


def make_output_filename(uploaded_name: str) -> str:
    base = os.path.basename(uploaded_name or "transcript")
    stem, _ = os.path.splitext(base)
    stem = unicodedata.normalize("NFKC", stem)
    stem = re.sub(r"[^A-Za-z0-9]+", "_", stem).strip("_")
    if not stem:
        stem = "transcript"
    return f"{stem}.txt"


def get_upload_size_bytes(file_obj) -> int:
    pos = file_obj.tell()
    file_obj.seek(0, os.SEEK_END)
    size = file_obj.tell()
    file_obj.seek(pos, os.SEEK_SET)
    return int(size)


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

    input_size_bytes = get_upload_size_bytes(file.file)

    try:
        gcs = upload_file(
            file_obj=file.file,
            destination_path=f"jobs/{job_id}/input/{file.filename}",
        )
    except Exception as exc:
        log(f"Job={job_id} upload_file failed: {exc}")
        raise HTTPException(status_code=503, detail="Failed to store upload input") from exc

    output_filename = make_output_filename(file.filename)
    source = "ocr" if type == "OCR" else "file"

    try:
        r.hset(
            f"job_status:{job_id}",
            mapping={
                "status": "QUEUED",
                "stage": "Queued",
                "progress": 0,
                "user": email,
                "job_type": type,
                "source": source,
                "input_filename": file.filename,
                "input_size_bytes": input_size_bytes,
                "output_filename": output_filename,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            },
        )
        r.lpush(f"user_jobs:{email}", job_id)
    except Exception as exc:
        log(f"Job={job_id} Redis status write failed: {exc}")
        raise HTTPException(status_code=503, detail="Queue metadata write failed") from exc

    payload = {
        "job_id": job_id,
        "job_type": type,
        "source": source,
        "input_gcs_uri": gcs["gcs_uri"],
        "filename": file.filename,
        "output_filename": output_filename,
        "input_size_bytes": input_size_bytes,
    }

    try:
        r.rpush(QUEUE_NAME, json.dumps(payload))
    except Exception as exc:
        log(f"Job={job_id} queue push failed: {exc}")
        raise HTTPException(status_code=503, detail="Queue push failed") from exc

    return {"job_id": job_id}
