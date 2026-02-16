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
from utils.metrics import incr
from utils.request_id import get_request_id
from utils.stage_logging import log_stage
from schemas.job_contract import CONTRACT_VERSION, JOB_TYPES, JOB_STATUS_QUEUED
from utils.status_machine import transition_hset

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
    if job_type not in JOB_TYPES:
        incr("api_jobs_submit_failed_total", reason="invalid_job_type", job_type=job_type or "")
        logger.warning("upload_validation_failed invalid_job_type type=%s", job_type)
        raise HTTPException(status_code=400, detail="Invalid job type")

    job_id = uuid.uuid4().hex
    email = user["email"].lower()
    request_id = get_request_id()

    log_stage(
        job_id=job_id,
        stage="UPLOAD_REQUEST",
        event="STARTED",
        user=email,
        job_type=job_type,
        filename=file.filename,
        queue=QUEUE_NAME,
        contract_version=CONTRACT_VERSION,
        request_id=request_id,
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
    except HTTPException:
        raise
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
        ok, current_status, _ = transition_hset(
            r,
            key=f"job_status:{job_id}",
            mapping={
                "contract_version": CONTRACT_VERSION,
                "status": JOB_STATUS_QUEUED,
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
                "request_id": request_id or "",
            },
            context="UPLOAD_INIT",
            request_id=request_id or "",
        )
        if not ok:
            raise HTTPException(status_code=409, detail=f"Invalid status transition to QUEUED from {current_status or 'NONE'}")
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
        "contract_version": CONTRACT_VERSION,
        "job_id": job_id,
        "job_type": job_type,
        "source": source,
        "input_gcs_uri": gcs["gcs_uri"],
        "filename": file.filename,
        "output_filename": output_filename,
        "input_size_bytes": input_size_bytes,
        "request_id": request_id or "",
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

    incr("api_jobs_submitted_total", job_type=job_type, source=source)
    log_stage(
        job_id=job_id,
        stage="UPLOAD_REQUEST",
        event="COMPLETED",
        user=email,
        job_type=job_type,
        source=source,
        contract_version=CONTRACT_VERSION,
        request_id=request_id,
    )

    return {"job_id": job_id, "request_id": request_id}
