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
from utils.stage_logging import log_stage

router = APIRouter()
logger = logging.getLogger("api.upload")

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
r = redis.Redis.from_url(REDIS_URL, decode_responses=True)

QUEUE_NAME = os.getenv("QUEUE_NAME", "doc_jobs")


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
    job_type: str = Form(..., alias="type"),
    user=Depends(verify_google_token),
):
    if job_type not in ("OCR", "TRANSCRIPTION"):
        logger.warning("upload_validation_failed invalid_job_type type=%s", job_type)
        raise HTTPException(status_code=400, detail="Invalid job type")

    job_id = uuid.uuid4().hex
    email = user["email"].lower()

    log_stage(
        job_id=job_id,
        stage="UPLOAD_REQUEST",
        event="STARTED",
        user=email,
        job_type=job_type,
        filename=file.filename,
        queue=QUEUE_NAME,
    )

    input_size_bytes = get_upload_size_bytes(file.file)

    log_stage(
        job_id=job_id,
        stage="INPUT_STORED_IN_GCS",
        event="STARTED",
        user=email,
        job_type=job_type,
        filename=file.filename,
        input_size_bytes=input_size_bytes,
    )
    try:
        gcs = upload_file(
            file_obj=file.file,
            destination_path=f"jobs/{job_id}/input/{file.filename}",
        )
        log_stage(
            job_id=job_id,
            stage="INPUT_STORED_IN_GCS",
            event="COMPLETED",
            user=email,
            job_type=job_type,
            input_gcs_uri=gcs.get("gcs_uri"),
        )
    except Exception as exc:
        log_stage(
            job_id=job_id,
            stage="INPUT_STORED_IN_GCS",
            event="FAILED",
            user=email,
            job_type=job_type,
            error=f"{exc.__class__.__name__}: {exc}",
        )
        raise HTTPException(status_code=503, detail="Failed to store upload input") from exc

    output_filename = make_output_filename(file.filename)
    source = "ocr" if job_type == "OCR" else "file"

    log_stage(
        job_id=job_id,
        stage="REDIS_JOB_METADATA",
        event="STARTED",
        user=email,
        job_type=job_type,
        source=source,
    )
    try:
        now_ts = datetime.utcnow().isoformat()
        r.hset(
            f"job_status:{job_id}",
            mapping={
                "status": "QUEUED",
                "stage": "Queued",
                "progress": 0,
                "user": email,
                "job_type": job_type,
                "source": source,
                "input_filename": file.filename,
                "input_size_bytes": input_size_bytes,
                "output_filename": output_filename,
                "created_at": now_ts,
                "updated_at": now_ts,
            },
        )
        r.lpush(f"user_jobs:{email}", job_id)
        log_stage(
            job_id=job_id,
            stage="REDIS_JOB_METADATA",
            event="COMPLETED",
            user=email,
            job_type=job_type,
            source=source,
        )
    except Exception as exc:
        log_stage(
            job_id=job_id,
            stage="REDIS_JOB_METADATA",
            event="FAILED",
            user=email,
            job_type=job_type,
            source=source,
            error=f"{exc.__class__.__name__}: {exc}",
        )
        raise HTTPException(status_code=503, detail="Queue metadata write failed") from exc

    payload = {
        "job_id": job_id,
        "job_type": job_type,
        "source": source,
        "input_gcs_uri": gcs["gcs_uri"],
        "filename": file.filename,
        "output_filename": output_filename,
        "input_size_bytes": input_size_bytes,
    }

    log_stage(
        job_id=job_id,
        stage="REDIS_QUEUE_ENQUEUE",
        event="STARTED",
        user=email,
        job_type=job_type,
        source=source,
        queue=QUEUE_NAME,
    )
    try:
        r.rpush(QUEUE_NAME, json.dumps(payload))
        queue_depth = r.llen(QUEUE_NAME)
        log_stage(
            job_id=job_id,
            stage="REDIS_QUEUE_ENQUEUE",
            event="COMPLETED",
            user=email,
            job_type=job_type,
            source=source,
            queue=QUEUE_NAME,
            queue_depth=queue_depth,
        )
    except Exception as exc:
        log_stage(
            job_id=job_id,
            stage="REDIS_QUEUE_ENQUEUE",
            event="FAILED",
            user=email,
            job_type=job_type,
            source=source,
            queue=QUEUE_NAME,
            error=f"{exc.__class__.__name__}: {exc}",
        )
        raise HTTPException(status_code=503, detail="Queue push failed") from exc

    log_stage(
        job_id=job_id,
        stage="UPLOAD_REQUEST",
        event="COMPLETED",
        user=email,
        job_type=job_type,
        source=source,
    )

    return {"job_id": job_id}
