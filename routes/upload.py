# routes/upload.py
import os
import re
import uuid
import json
import redis
import logging
import hashlib
import unicodedata
from datetime import datetime

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, Header

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
IDEMPOTENCY_TTL_SEC = int(os.getenv("IDEMPOTENCY_TTL_SEC", "900"))


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


def normalize_idempotency_key(raw: str | None) -> str:
    if not raw:
        return ""
    key = re.sub(r"[^A-Za-z0-9_.:-]", "", str(raw).strip())
    return key[:128]


def idempotency_redis_key(email: str, job_type: str, idem_key: str) -> str:
    return f"upload_idempotency:{email}:{job_type}:{idem_key}"


def derive_idempotent_job_id(email: str, job_type: str, idem_key: str) -> str:
    digest = hashlib.sha256(f"{email}|{job_type}|{idem_key}".encode("utf-8")).hexdigest()
    return digest[:32]


def try_reuse_idempotent_job(*, email: str, job_type: str, idem_key: str, request_id: str) -> dict | None:
    map_key = idempotency_redis_key(email, job_type, idem_key)
    existing_job_id = r.get(map_key)

    def _build_reuse_response(job_id: str, data: dict) -> dict:
        reused_request_id = str(data.get("request_id") or request_id or "")
        return {"job_id": job_id, "request_id": reused_request_id, "reused": True}

    if existing_job_id:
        data = r.hgetall(f"job_status:{existing_job_id}")
        if data and data.get("user") == email and (data.get("job_type") or "").upper() == job_type:
            r.expire(map_key, IDEMPOTENCY_TTL_SEC)
            log_stage(
                job_id=existing_job_id,
                stage="UPLOAD_IDEMPOTENCY",
                event="COMPLETED",
                user=email,
                job_type=job_type,
                request_id=request_id,
                message="duplicate_reused_cached_key",
            )
            incr("api_jobs_idempotent_reused_total", job_type=job_type)
            return _build_reuse_response(existing_job_id, data)

        # stale mapping
        r.delete(map_key)

    deterministic_job_id = derive_idempotent_job_id(email, job_type, idem_key)
    existing = r.hgetall(f"job_status:{deterministic_job_id}")
    if existing and existing.get("user") == email and (existing.get("job_type") or "").upper() == job_type:
        r.set(map_key, deterministic_job_id, ex=IDEMPOTENCY_TTL_SEC)
        log_stage(
            job_id=deterministic_job_id,
            stage="UPLOAD_IDEMPOTENCY",
            event="COMPLETED",
            user=email,
            job_type=job_type,
            request_id=request_id,
            message="duplicate_reused_deterministic_key",
        )
        incr("api_jobs_idempotent_reused_total", job_type=job_type)
        return _build_reuse_response(deterministic_job_id, existing)

    return None


@router.post("/upload")
async def upload(
    file: UploadFile = File(...),
    job_type: str = Form(..., alias="type"),
    idempotency_key: str | None = Header(default=None, alias="X-Idempotency-Key"),
    user=Depends(verify_google_token),
):
    if job_type not in JOB_TYPES:
        incr("api_jobs_submit_failed_total", reason="invalid_job_type", job_type=job_type or "")
        logger.warning("upload_validation_failed invalid_job_type type=%s", job_type)
        raise HTTPException(status_code=400, detail="Invalid job type")

    email = user["email"].lower()
    request_id = get_request_id()
    idem_key = normalize_idempotency_key(idempotency_key)

    if idem_key:
        log_stage(
            job_id="idempotency-check",
            stage="UPLOAD_IDEMPOTENCY",
            event="STARTED",
            user=email,
            job_type=job_type,
            request_id=request_id,
        )
        reused = try_reuse_idempotent_job(email=email, job_type=job_type, idem_key=idem_key, request_id=request_id)
        if reused:
            return reused

    job_id = derive_idempotent_job_id(email, job_type, idem_key) if idem_key else uuid.uuid4().hex

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

        if idem_key:
            r.set(idempotency_redis_key(email, job_type, idem_key), job_id, ex=IDEMPOTENCY_TTL_SEC)

        r.lpush(f"user_jobs:{email}", job_id)
        log_stage(
            job_id=job_id,
            stage="REDIS_JOB_METADATA",
            event="COMPLETED",
            user=email,
            job_type=job_type,
            source=source,
        )
    except HTTPException:
        raise
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
        enqueue_guard_key = f"job_enqueue_once:{job_id}"
        enqueue_ttl = IDEMPOTENCY_TTL_SEC if idem_key else 24 * 3600
        should_enqueue = r.set(enqueue_guard_key, "1", nx=True, ex=enqueue_ttl)
        if should_enqueue:
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
        else:
            log_stage(
                job_id=job_id,
                stage="REDIS_QUEUE_ENQUEUE",
                event="COMPLETED",
                user=email,
                job_type=job_type,
                source=source,
                queue=QUEUE_NAME,
                message="duplicate_enqueue_skipped",
            )
            incr("api_jobs_idempotent_reused_total", job_type=job_type)
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

    return {"job_id": job_id, "request_id": request_id, "reused": False}
