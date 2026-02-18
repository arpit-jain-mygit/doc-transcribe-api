# User value: This file helps users get reliable OCR/transcription results with clear processing behavior.
# services/upload_orchestrator.py
import hashlib
import json
import logging
import os
import re
import unicodedata
import uuid
from datetime import datetime

import redis
from fastapi import HTTPException, UploadFile

from schemas.job_contract import CONTRACT_VERSION, JOB_TYPES, JOB_STATUS_QUEUED
from services.feature_flags import (
    FEATURE_DURATION_PAGE_LIMITS,
    FEATURE_QUEUE_PARTITIONING,
    FEATURE_UPLOAD_QUOTAS,
)
from services.gcs import upload_file
from services.intake_precheck import build_precheck_warnings
from services.intake_router import (
    OCR_EXTENSIONS as ALLOWED_OCR_EXTENSIONS,
    TRANSCRIPTION_EXTENSIONS as ALLOWED_TRANSCRIPTION_EXTENSIONS,
    OCR_MIME_PREFIXES as ALLOWED_OCR_MIME_PREFIXES,
    TRANSCRIPTION_MIME_PREFIXES as ALLOWED_TRANSCRIPTION_MIME_PREFIXES,
    detect_route_from_metadata,
)
from services.quota import enforce_pages_and_duration_limits, enforce_upload_quotas, register_daily_job_usage
from utils.metrics import incr
from utils.stage_logging import log_stage
from utils.status_machine import transition_hset

logger = logging.getLogger("api.upload")

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
r = redis.Redis.from_url(REDIS_URL, decode_responses=True)

QUEUE_NAME = os.getenv("QUEUE_NAME", "doc_jobs")
QUEUE_NAME_OCR = os.getenv("QUEUE_NAME_OCR", "doc_jobs_ocr")
QUEUE_NAME_TRANSCRIPTION = os.getenv("QUEUE_NAME_TRANSCRIPTION", "doc_jobs_transcription")
IDEMPOTENCY_TTL_SEC = int(os.getenv("IDEMPOTENCY_TTL_SEC", "900"))

MAX_OCR_FILE_SIZE_MB = int(os.getenv("MAX_OCR_FILE_SIZE_MB", "25"))
MAX_TRANSCRIPTION_FILE_SIZE_MB = int(os.getenv("MAX_TRANSCRIPTION_FILE_SIZE_MB", "100"))
MAX_OCR_FILE_SIZE_BYTES = MAX_OCR_FILE_SIZE_MB * 1024 * 1024
MAX_TRANSCRIPTION_FILE_SIZE_BYTES = MAX_TRANSCRIPTION_FILE_SIZE_MB * 1024 * 1024


# User value: routes work so user OCR/transcription jobs are processed correctly.
def resolve_target_queue(job_type: str) -> str:
    if not FEATURE_QUEUE_PARTITIONING:
        return QUEUE_NAME
    if job_type == "OCR":
        return QUEUE_NAME_OCR
    return QUEUE_NAME_TRANSCRIPTION


# User value: normalizes data so users see consistent OCR/transcription results.
def _parse_pdf_page_count(file_obj) -> int | None:
    try:
        pos = file_obj.tell()
        file_obj.seek(0, os.SEEK_SET)
        blob = file_obj.read()
        file_obj.seek(pos, os.SEEK_SET)
        if not blob:
            return None
        text = blob.decode("latin-1", errors="ignore")
        # Lightweight heuristic to avoid adding heavy PDF dependency at API layer.
        count = text.count("/Type /Page")
        if count <= 0:
            return None
        # Some PDFs include "/Pages" nodes; keep floor at 1 for valid matches.
        return max(1, count - text.count("/Type /Pages"))
    except Exception:
        return None


# User value: supports derive_total_pages so the OCR/transcription journey stays clear and reliable.
def derive_total_pages(file: UploadFile, job_type: str) -> int | None:
    if job_type != "OCR":
        return None
    ext = _extension(file.filename)
    if ext == ".pdf":
        return _parse_pdf_page_count(file.file)
    return 1


# User value: supports make_output_filename so the OCR/transcription journey stays clear and reliable.
def make_output_filename(uploaded_name: str) -> str:
    base = os.path.basename(uploaded_name or "transcript")
    stem, _ = os.path.splitext(base)
    stem = unicodedata.normalize("NFKC", stem)
    stem = re.sub(r"[^A-Za-z0-9]+", "_", stem).strip("_")
    if not stem:
        stem = "transcript"
    return f"{stem}.txt"


# User value: loads latest OCR/transcription data so users see current status.
def get_upload_size_bytes(file_obj) -> int:
    pos = file_obj.tell()
    file_obj.seek(0, os.SEEK_END)
    size = file_obj.tell()
    file_obj.seek(pos, os.SEEK_SET)
    return int(size)


# User value: supports _bad_request so the OCR/transcription journey stays clear and reliable.
def _bad_request(error_code: str, message: str) -> HTTPException:
    return HTTPException(status_code=400, detail={"error_code": error_code, "error_message": message})


# User value: supports _extension so the OCR/transcription journey stays clear and reliable.
def _extension(filename: str | None) -> str:
    return os.path.splitext(str(filename or "").strip().lower())[1]


# User value: supports _mime_allowed so the OCR/transcription journey stays clear and reliable.
def _mime_allowed(content_type: str | None, prefixes: tuple[str, ...]) -> bool:
    mime = str(content_type or "").strip().lower()
    if not mime:
        return False
    return any(mime.startswith(prefix) for prefix in prefixes)


# User value: submits user files safely for OCR/transcription processing.
def validate_upload_constraints(file: UploadFile, job_type: str, input_size_bytes: int) -> None:
    filename = str(file.filename or "").strip()
    if not filename:
        raise _bad_request("INVALID_FILENAME", "Filename is required")

    ext = _extension(filename)
    mime = str(file.content_type or "").strip().lower()

    if job_type == "OCR":
        if ext not in ALLOWED_OCR_EXTENSIONS:
            raise _bad_request(
                "UNSUPPORTED_FILE_TYPE",
                f"OCR supports: {', '.join(sorted(ALLOWED_OCR_EXTENSIONS))}",
            )
        if mime and not _mime_allowed(mime, ALLOWED_OCR_MIME_PREFIXES):
            raise _bad_request("UNSUPPORTED_MIME_TYPE", f"Unsupported OCR MIME type: {mime}")
        if input_size_bytes > MAX_OCR_FILE_SIZE_BYTES:
            raise _bad_request(
                "FILE_TOO_LARGE",
                f"OCR file exceeds max {MAX_OCR_FILE_SIZE_MB} MB",
            )
        return

    if job_type == "TRANSCRIPTION":
        if ext not in ALLOWED_TRANSCRIPTION_EXTENSIONS:
            raise _bad_request(
                "UNSUPPORTED_FILE_TYPE",
                f"Transcription supports: {', '.join(sorted(ALLOWED_TRANSCRIPTION_EXTENSIONS))}",
            )
        if mime and not _mime_allowed(mime, ALLOWED_TRANSCRIPTION_MIME_PREFIXES):
            raise _bad_request("UNSUPPORTED_MIME_TYPE", f"Unsupported transcription MIME type: {mime}")
        if input_size_bytes > MAX_TRANSCRIPTION_FILE_SIZE_BYTES:
            raise _bad_request(
                "FILE_TOO_LARGE",
                f"Transcription file exceeds max {MAX_TRANSCRIPTION_FILE_SIZE_MB} MB",
            )
        return

    raise _bad_request("INVALID_JOB_TYPE", "Invalid job type")


# User value: normalizes data so users see consistent OCR/transcription results.
def normalize_idempotency_key(raw: str | None) -> str:
    if not raw:
        return ""
    key = re.sub(r"[^A-Za-z0-9_.:-]", "", str(raw).strip())
    return key[:128]


# User value: supports idempotency_redis_key so the OCR/transcription journey stays clear and reliable.
def idempotency_redis_key(email: str, job_type: str, idem_key: str) -> str:
    return f"upload_idempotency:{email}:{job_type}:{idem_key}"


# User value: supports derive_idempotent_job_id so the OCR/transcription journey stays clear and reliable.
def derive_idempotent_job_id(email: str, job_type: str, idem_key: str) -> str:
    digest = hashlib.sha256(f"{email}|{job_type}|{idem_key}".encode("utf-8")).hexdigest()
    return digest[:32]


# User value: supports _build_reuse_response so the OCR/transcription journey stays clear and reliable.
def _build_reuse_response(job_id: str, data: dict, request_id: str) -> dict:
    reused_request_id = str(data.get("request_id") or request_id or "")
    return {"job_id": job_id, "request_id": reused_request_id, "reused": True}


# User value: supports try_reuse_idempotent_job so the OCR/transcription journey stays clear and reliable.
def try_reuse_idempotent_job(*, email: str, job_type: str, idem_key: str, request_id: str) -> dict | None:
    map_key = idempotency_redis_key(email, job_type, idem_key)
    existing_job_id = r.get(map_key)

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
            return _build_reuse_response(existing_job_id, data, request_id)

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
        return _build_reuse_response(deterministic_job_id, existing, request_id)

    return None


# User value: submits user files safely for OCR/transcription processing.
def submit_upload_job(
    *,
    file: UploadFile,
    job_type: str,
    email: str,
    request_id: str,
    idempotency_key: str | None,
    media_duration_sec: float | None = None,
) -> dict:
    if job_type not in JOB_TYPES:
        incr("api_jobs_submit_failed_total", reason="invalid_job_type", job_type=job_type or "")
        logger.warning("upload_validation_failed invalid_job_type type=%s", job_type)
        raise HTTPException(status_code=400, detail="Invalid job type")

    user_email = email.lower()
    queue_name = resolve_target_queue(job_type)
    idem_key = normalize_idempotency_key(idempotency_key)

    if idem_key:
        log_stage(
            job_id="idempotency-check",
            stage="UPLOAD_IDEMPOTENCY",
            event="STARTED",
            user=user_email,
            job_type=job_type,
            request_id=request_id,
        )
        reused = try_reuse_idempotent_job(
            email=user_email, job_type=job_type, idem_key=idem_key, request_id=request_id
        )
        if reused:
            return reused

    job_id = derive_idempotent_job_id(user_email, job_type, idem_key) if idem_key else uuid.uuid4().hex

    log_stage(
        job_id=job_id,
        stage="UPLOAD_REQUEST",
        event="STARTED",
        user=user_email,
        job_type=job_type,
        filename=file.filename,
        queue=queue_name,
        contract_version=CONTRACT_VERSION,
        request_id=request_id,
    )

    if FEATURE_UPLOAD_QUOTAS:
        enforce_upload_quotas(r=r, email=user_email, request_id=request_id or "", job_type=job_type)

    route_detection = detect_route_from_metadata(file.filename, file.content_type)
    log_stage(
        job_id=job_id,
        stage="UPLOAD_ROUTE_DETECT",
        event="COMPLETED",
        user=user_email,
        job_type=job_type,
        filename=file.filename,
        request_id=request_id,
        detected_job_type=route_detection.get("detected_job_type", "UNKNOWN"),
        confidence=route_detection.get("confidence", 0.0),
        reasons="|".join(route_detection.get("reasons") or []),
    )

    input_size_bytes = get_upload_size_bytes(file.file)
    total_pages = derive_total_pages(file, job_type)

    precheck_warnings = build_precheck_warnings(
        job_type=job_type,
        filename=file.filename,
        mime_type=file.content_type,
        file_size_bytes=input_size_bytes,
        media_duration_sec=media_duration_sec,
        pdf_page_count=total_pages,
    )
    if precheck_warnings:
        log_stage(
            job_id=job_id,
            stage="UPLOAD_PRECHECK_WARNINGS",
            event="COMPLETED",
            user=user_email,
            job_type=job_type,
            filename=file.filename,
            request_id=request_id,
            warning_codes="|".join(w.get("code", "") for w in precheck_warnings),
            warning_count=len(precheck_warnings),
        )
    if FEATURE_DURATION_PAGE_LIMITS:
        enforce_pages_and_duration_limits(
            job_type=job_type,
            total_pages=total_pages,
            media_duration_sec=media_duration_sec,
        )
    try:
        validate_upload_constraints(file=file, job_type=job_type, input_size_bytes=input_size_bytes)
    except HTTPException as exc:
        incr("api_jobs_submit_failed_total", reason="upload_validation_failed", job_type=job_type or "")
        log_stage(
            job_id=job_id,
            stage="UPLOAD_VALIDATION",
            event="FAILED",
            user=user_email,
            job_type=job_type,
            filename=file.filename,
            input_size_bytes=input_size_bytes,
            request_id=request_id,
            error=str(exc.detail),
        )
        raise

    log_stage(
        job_id=job_id,
        stage="INPUT_STORED_IN_GCS",
        event="STARTED",
        user=user_email,
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
            user=user_email,
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
            user=user_email,
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
        user=user_email,
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
                "user": user_email,
                "job_type": job_type,
                "source": source,
                "input_filename": file.filename,
                "input_size_bytes": input_size_bytes,
                "output_filename": output_filename,
                "total_pages": total_pages if total_pages is not None else "",
                "duration_sec": media_duration_sec if media_duration_sec is not None else "",
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
            r.set(idempotency_redis_key(user_email, job_type, idem_key), job_id, ex=IDEMPOTENCY_TTL_SEC)
        register_daily_job_usage(r=r, email=user_email)

        r.lpush(f"user_jobs:{user_email}", job_id)
        log_stage(
            job_id=job_id,
            stage="REDIS_JOB_METADATA",
            event="COMPLETED",
            user=user_email,
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
            user=user_email,
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
        "queue": queue_name,
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
        user=user_email,
        job_type=job_type,
        source=source,
        queue=queue_name,
    )
    try:
        enqueue_guard_key = f"job_enqueue_once:{job_id}"
        enqueue_ttl = IDEMPOTENCY_TTL_SEC if idem_key else 24 * 3600
        should_enqueue = r.set(enqueue_guard_key, "1", nx=True, ex=enqueue_ttl)
        if should_enqueue:
            r.rpush(queue_name, json.dumps(payload))
            queue_depth = r.llen(queue_name)
            log_stage(
                job_id=job_id,
                stage="REDIS_QUEUE_ENQUEUE",
                event="COMPLETED",
                user=user_email,
                job_type=job_type,
                source=source,
                queue=queue_name,
                queue_depth=queue_depth,
            )
        else:
            log_stage(
                job_id=job_id,
                stage="REDIS_QUEUE_ENQUEUE",
                event="COMPLETED",
                user=user_email,
                job_type=job_type,
                source=source,
                queue=queue_name,
                message="duplicate_enqueue_skipped",
            )
            incr("api_jobs_idempotent_reused_total", job_type=job_type)
    except Exception as exc:
        log_stage(
            job_id=job_id,
            stage="REDIS_QUEUE_ENQUEUE",
            event="FAILED",
            user=user_email,
            job_type=job_type,
            source=source,
            queue=queue_name,
            error=f"{exc.__class__.__name__}: {exc}",
        )
        raise HTTPException(status_code=503, detail="Queue push failed") from exc

    incr("api_jobs_submitted_total", job_type=job_type, source=source)
    log_stage(
        job_id=job_id,
        stage="UPLOAD_REQUEST",
        event="COMPLETED",
        user=user_email,
        job_type=job_type,
        source=source,
        contract_version=CONTRACT_VERSION,
        request_id=request_id,
    )

    return {"job_id": job_id, "request_id": request_id, "reused": False}
