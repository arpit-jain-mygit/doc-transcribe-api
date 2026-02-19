# User value: This file helps users get reliable OCR/transcription results with clear processing behavior.
# routes/jobs.py
import os
import json
import uuid
import redis
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query

from services.auth import verify_google_token
from services.gcs import generate_signed_url
from utils.metrics import incr
from utils.request_id import get_request_id
from utils.stage_logging import log_stage
from schemas.job_contract import (
    TRACKED_HISTORY_STATUSES,
    TERMINAL_STATUSES,
    JOB_STATUS_CANCELLED,
    JOB_STATUS_QUEUED,
)
from utils.status_machine import transition_hset
from utils.request_id import get_request_id

router = APIRouter()

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
r = redis.Redis.from_url(REDIS_URL, decode_responses=True)
QUEUE_NAME = os.getenv("QUEUE_NAME", "doc_jobs")
QUEUE_NAME_OCR = os.getenv("QUEUE_NAME_OCR", "doc_jobs_ocr")
QUEUE_NAME_TRANSCRIPTION = os.getenv("QUEUE_NAME_TRANSCRIPTION", "doc_jobs_transcription")
FEATURE_QUEUE_PARTITIONING = str(os.getenv("FEATURE_QUEUE_PARTITIONING", "1")).strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME", "doc-transcribe-output-transcribe-serverless").strip()


# User value: routes retried jobs to the right worker queue so retries are processed quickly and correctly.
def resolve_target_queue(job_type: str) -> str:
    if not FEATURE_QUEUE_PARTITIONING:
        return QUEUE_NAME
    if str(job_type or "").upper() == "OCR":
        return QUEUE_NAME_OCR
    return QUEUE_NAME_TRANSCRIPTION


@router.get("/jobs")
# User value: supports list_jobs so the OCR/transcription journey stays clear and reliable.
def list_jobs(
    user=Depends(verify_google_token),
    job_type: str | None = Query(default=None, description="Filter by job type, e.g. TRANSCRIPTION/OCR"),
    status: str | None = Query(default=None, description="Filter by status, e.g. COMPLETED/FAILED/CANCELLED"),
    limit: int | None = Query(default=None, ge=1, le=200, description="Page size for load-more"),
    offset: int = Query(default=0, ge=0, description="Offset for load-more"),
    include_counts: bool = Query(default=False, description="Include counts_by_status in response"),
):
    email = user["email"].lower()
    status_norm = status.strip().upper() if status else None
    job_type_norm = job_type.strip().upper() if job_type else None

    log_stage(
        job_id="jobs-list",
        stage="JOBS_LIST",
        event="STARTED",
        user=email,
        requested_status=status,
        requested_job_type=job_type,
        limit=limit,
        offset=offset,
        include_counts=include_counts,
    )

    user_jobs_key = f"user_jobs:{email}"
    total_user_jobs = r.llen(user_jobs_key)

    # User value: supports enrich so the OCR/transcription journey stays clear and reliable.
    def enrich(job_id: str, data: dict) -> dict:
        if not data.get("request_id"):
            rid = get_request_id()
            if rid:
                data["request_id"] = rid
        output_path = data.get("output_path")
        if output_path and output_path.startswith("gs://"):
            path = output_path.replace("gs://", "")
            bucket, blob = path.split("/", 1)
            filename = data.get("output_filename") or os.path.basename(blob) or "transcript.txt"

            signed_url = generate_signed_url(
                bucket_name=bucket,
                blob_path=blob,
                expiration_minutes=60,
                download_filename=filename,
            )

            data["output_path"] = signed_url
            data["download_url"] = signed_url

        data["job_id"] = job_id
        trace_raw = data.get("recovery_trace")
        if not isinstance(trace_raw, list):
            text = str(trace_raw or "").strip()
            if text:
                try:
                    parsed = json.loads(text)
                    data["recovery_trace"] = parsed if isinstance(parsed, list) else []
                except Exception:
                    data["recovery_trace"] = []
            else:
                data["recovery_trace"] = []
        return data

    # Backward compatibility: when no pagination requested, return full array.
    if limit is None:
        job_ids = r.lrange(user_jobs_key, 0, -1)
        jobs = []
        for job_id in job_ids:
            data = r.hgetall(f"job_status:{job_id}")
            if not data:
                continue
            jobs.append(enrich(job_id, data))

        incr("api_jobs_list_total", mode="all", include_counts="false", filtered="false")
        log_stage(
            job_id="jobs-list",
            stage="JOBS_LIST",
            event="COMPLETED",
            user=email,
            returned_count=len(jobs),
            paginated=False,
            total_user_jobs=total_user_jobs,
            scanned_count=len(job_ids),
            fast_path=False,
        )
        return jobs

    # Fast path for primary UI use-case: paginated, no filters, no counts.
    if not include_counts and not status_norm and not job_type_norm:
        selected_job_ids = r.lrange(user_jobs_key, offset, offset + limit)
        has_more = len(selected_job_ids) > limit
        page_job_ids = selected_job_ids[:limit]

        details_pipe = r.pipeline(transaction=False)
        for job_id in page_job_ids:
            details_pipe.hgetall(f"job_status:{job_id}")
        details_rows = details_pipe.execute()

        items = []
        for idx, data in enumerate(details_rows):
            if not data:
                continue
            items.append(enrich(page_job_ids[idx], data))

        response = {
            "items": items,
            "offset": offset,
            "limit": limit,
            "next_offset": (offset + len(items)) if has_more else None,
            "has_more": has_more,
            "total": None,
        }

        incr("api_jobs_list_total", mode="paged", include_counts="false", filtered="false")
        log_stage(
            job_id="jobs-list",
            stage="JOBS_LIST",
            event="COMPLETED",
            user=email,
            returned_count=len(items),
            paginated=True,
            has_more=has_more,
            next_offset=response.get("next_offset"),
            total_user_jobs=total_user_jobs,
            scanned_count=len(selected_job_ids),
            fast_path=True,
        )
        return response

    counts_by_status = {k: 0 for k in TRACKED_HISTORY_STATUSES}
    counts_by_type = {"TRANSCRIPTION": 0, "OCR": 0}

    selected_job_ids: list[str] = []
    matched_seen = 0
    matched_total = 0
    scanned_count = 0

    job_ids = r.lrange(user_jobs_key, 0, -1)

    if include_counts:
        meta_pipe = r.pipeline(transaction=False)
        for job_id in job_ids:
            meta_pipe.hmget(f"job_status:{job_id}", "status", "job_type", "type")
        meta_rows = meta_pipe.execute()
    else:
        meta_rows = None

    for idx, job_id in enumerate(job_ids):
        scanned_count += 1

        if include_counts:
            row = meta_rows[idx]
        else:
            row = r.hmget(f"job_status:{job_id}", "status", "job_type", "type")

        if not row:
            continue

        row_status = (row[0] or "").upper()
        row_type = (row[1] or row[2] or "").upper()
        if include_counts and row_type in counts_by_type:
            counts_by_type[row_type] += 1

        if job_type_norm and row_type != job_type_norm:
            continue

        if include_counts and row_status in counts_by_status:
            counts_by_status[row_status] += 1

        if status_norm and row_status != status_norm:
            continue

        matched_total += 1

        if matched_seen < offset:
            matched_seen += 1
            continue

        if len(selected_job_ids) < (limit + 1):
            selected_job_ids.append(job_id)
            matched_seen += 1
            continue

        if not include_counts:
            break

    has_more = len(selected_job_ids) > limit
    page_job_ids = selected_job_ids[:limit]

    details_pipe = r.pipeline(transaction=False)
    for job_id in page_job_ids:
        details_pipe.hgetall(f"job_status:{job_id}")
    details_rows = details_pipe.execute()

    items = []
    for idx, data in enumerate(details_rows):
        if not data:
            continue
        items.append(enrich(page_job_ids[idx], data))

    if include_counts:
        has_more = (offset + len(items)) < matched_total

    response = {
        "items": items,
        "offset": offset,
        "limit": limit,
        "next_offset": (offset + len(items)) if has_more else None,
        "has_more": has_more,
        "total": matched_total if include_counts else None,
    }

    if include_counts:
        response["counts_by_status"] = counts_by_status
        response["counts_by_type"] = counts_by_type

    incr(
        "api_jobs_list_total",
        mode="paged",
        include_counts="true" if include_counts else "false",
        filtered="true" if (status_norm or job_type_norm) else "false",
    )
    log_stage(
        job_id="jobs-list",
        stage="JOBS_LIST",
        event="COMPLETED",
        user=email,
        returned_count=len(items),
        paginated=True,
        has_more=has_more,
        next_offset=response.get("next_offset"),
        total_user_jobs=total_user_jobs,
        scanned_count=scanned_count,
        matched_total=matched_total,
        fast_path=False,
    )
    return response


@router.post("/jobs/{job_id}/cancel")
# User value: lets users stop running OCR/transcription jobs quickly.
def cancel_job(job_id: str, user=Depends(verify_google_token)):
    email = user["email"].lower()
    log_stage(job_id=job_id, stage="JOB_CANCEL", event="STARTED", user=email)

    key = f"job_status:{job_id}"
    data = r.hgetall(key)

    if not data:
        incr("api_jobs_cancel_failed_total", reason="not_found")
        log_stage(job_id=job_id, stage="JOB_CANCEL", event="FAILED", user=email, error="Job not found")
        raise HTTPException(status_code=404, detail="Job not found")

    if data.get("user") != email:
        incr("api_jobs_cancel_failed_total", reason="forbidden")
        log_stage(job_id=job_id, stage="JOB_CANCEL", event="FAILED", user=email, error="Forbidden")
        raise HTTPException(status_code=403, detail="Forbidden")

    status = (data.get("status") or "").upper()
    if status in TERMINAL_STATUSES:
        incr("api_jobs_cancel_noop_total", status=status)
        log_stage(
            job_id=job_id,
            stage="JOB_CANCEL",
            event="COMPLETED",
            user=email,
            status=status,
            message="already_finished",
        )
        return {
            "job_id": job_id,
            "status": status,
            "message": "Job already finished",
        }
    ok, current_status, _ = transition_hset(
        r,
        key=key,
        mapping={
            "cancel_requested": "1",
            "status": JOB_STATUS_CANCELLED,
            "stage": "Cancelled by user",
            "updated_at": datetime.utcnow().isoformat(),
        },
        context="JOB_CANCEL",
        request_id=str(data.get("request_id") or ""),
    )
    if not ok:
        raise HTTPException(status_code=409, detail=f"Invalid status transition to CANCELLED from {current_status or 'NONE'}")
    incr("api_jobs_cancel_requested_total", prior_status=status or "UNKNOWN")

    log_stage(job_id=job_id, stage="JOB_CANCEL", event="COMPLETED", user=email, status=JOB_STATUS_CANCELLED)
    return {
        "job_id": job_id,
        "status": JOB_STATUS_CANCELLED,
        "message": "Cancellation requested",
    }


@router.post("/jobs/{job_id}/retry")
# User value: lets users quickly retry failed/cancelled OCR/transcription jobs without re-uploading files.
def retry_job(job_id: str, user=Depends(verify_google_token)):
    email = user["email"].lower()
    request_id = get_request_id()
    log_stage(job_id=job_id, stage="JOB_RETRY", event="STARTED", user=email, request_id=request_id)

    key = f"job_status:{job_id}"
    data = r.hgetall(key)
    if not data:
        incr("api_jobs_retry_failed_total", reason="not_found")
        raise HTTPException(status_code=404, detail="Job not found")
    if data.get("user") != email:
        incr("api_jobs_retry_failed_total", reason="forbidden")
        raise HTTPException(status_code=403, detail="Forbidden")

    status = str(data.get("status") or "").upper()
    if status not in {"FAILED", "CANCELLED"}:
        incr("api_jobs_retry_failed_total", reason="invalid_status", status=status or "UNKNOWN")
        raise HTTPException(status_code=409, detail=f"Retry allowed only for FAILED/CANCELLED jobs (current={status or 'UNKNOWN'})")

    job_type = str(data.get("job_type") or "OCR").upper()
    queue_name = resolve_target_queue(job_type)
    source = str(data.get("source") or ("ocr" if job_type == "OCR" else "file"))
    input_filename = str(data.get("input_filename") or "")
    output_filename = str(data.get("output_filename") or "transcript.txt")
    input_size_bytes = str(data.get("input_size_bytes") or "")
    total_pages = str(data.get("total_pages") or "")
    media_duration = str(data.get("duration_sec") or "")

    input_gcs_uri = str(data.get("input_gcs_uri") or "").strip()
    if not input_gcs_uri:
        input_gcs_uri = f"gs://{GCS_BUCKET_NAME}/jobs/{job_id}/input/{input_filename}"

    retry_job_id = uuid.uuid4().hex
    now_ts = datetime.utcnow().isoformat()
    retry_key = f"job_status:{retry_job_id}"

    try:
        ok, current_status, _ = transition_hset(
            r,
            key=retry_key,
            mapping={
                "status": JOB_STATUS_QUEUED,
                "stage": "Queued",
                "progress": 0,
                "user": email,
                "job_type": job_type,
                "source": source,
                "input_filename": input_filename,
                "input_size_bytes": input_size_bytes,
                "output_filename": output_filename,
                "total_pages": total_pages,
                "duration_sec": media_duration,
                "created_at": now_ts,
                "updated_at": now_ts,
                "request_id": request_id or "",
                "retry_of_job_id": job_id,
            },
            context="JOB_RETRY_INIT",
            request_id=request_id or "",
        )
        if not ok:
            raise HTTPException(status_code=409, detail=f"Invalid status transition to QUEUED from {current_status or 'NONE'}")

        r.lpush(f"user_jobs:{email}", retry_job_id)
        payload = {
            "job_id": retry_job_id,
            "job_type": job_type,
            "source": source,
            "queue": queue_name,
            "input_gcs_uri": input_gcs_uri,
            "filename": input_filename,
            "output_filename": output_filename,
            "input_size_bytes": input_size_bytes,
            "request_id": request_id or "",
            "retry_of_job_id": job_id,
        }
        r.rpush(queue_name, json.dumps(payload, ensure_ascii=False))
        incr("api_jobs_retry_requested_total", job_type=job_type, source=source, queue=queue_name)
    except HTTPException:
        raise
    except Exception as exc:
        incr("api_jobs_retry_failed_total", reason="queue_or_metadata_error")
        raise HTTPException(status_code=503, detail=f"Retry request failed: {exc.__class__.__name__}") from exc

    log_stage(
        job_id=retry_job_id,
        stage="JOB_RETRY",
        event="COMPLETED",
        user=email,
        request_id=request_id,
        retry_of_job_id=job_id,
        queue=queue_name,
        job_type=job_type,
    )
    return {"job_id": retry_job_id, "request_id": request_id, "retry_of_job_id": job_id}
