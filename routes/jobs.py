# routes/jobs.py
import os
import redis
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query

from services.auth import verify_google_token
from services.gcs import generate_signed_url
from utils.stage_logging import log_stage
from schemas.job_contract import (
    TRACKED_HISTORY_STATUSES,
    TERMINAL_STATUSES,
    JOB_STATUS_CANCELLED,
)

router = APIRouter()

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
r = redis.Redis.from_url(REDIS_URL, decode_responses=True)


@router.get("/jobs")
def list_jobs(
    user=Depends(verify_google_token),
    job_type: str | None = Query(default=None, description="Filter by job type, e.g. TRANSCRIPTION/OCR"),
    status: str | None = Query(default=None, description="Filter by status, e.g. COMPLETED/FAILED/CANCELLED"),
    limit: int | None = Query(default=None, ge=1, le=200, description="Page size for load-more"),
    offset: int = Query(default=0, ge=0, description="Offset for load-more"),
    include_counts: bool = Query(default=False, description="Include counts_by_status in response"),
):
    email = user["email"].lower()
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

    job_ids = r.lrange(f"user_jobs:{email}", 0, -1)

    def enrich(job_id: str, data: dict) -> dict:
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
        return data

    # Backward compatibility: when no pagination requested, return full array.
    if limit is None:
        jobs = []
        for job_id in job_ids:
            data = r.hgetall(f"job_status:{job_id}")
            if not data:
                continue
            jobs.append(enrich(job_id, data))

        log_stage(
            job_id="jobs-list",
            stage="JOBS_LIST",
            event="COMPLETED",
            user=email,
            returned_count=len(jobs),
            paginated=False,
        )
        return jobs

    status_norm = status.strip().upper() if status else None
    job_type_norm = job_type.strip().upper() if job_type else None
    counts_by_status = {k: 0 for k in TRACKED_HISTORY_STATUSES}
    counts_by_type = {"TRANSCRIPTION": 0, "OCR": 0}

    selected_job_ids: list[str] = []
    matched_seen = 0
    matched_total = 0

    meta_pipe = r.pipeline(transaction=False)
    for job_id in job_ids:
        meta_pipe.hmget(f"job_status:{job_id}", "status", "job_type", "type")
    meta_rows = meta_pipe.execute()

    for idx, job_id in enumerate(job_ids):
        row = meta_rows[idx]
        if not row:
            continue

        row_status = (row[0] or "").upper()
        row_type = (row[1] or row[2] or "").upper()
        if include_counts:
            if row_type in counts_by_type:
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

    log_stage(
        job_id="jobs-list",
        stage="JOBS_LIST",
        event="COMPLETED",
        user=email,
        returned_count=len(items),
        paginated=True,
        has_more=has_more,
        next_offset=response.get("next_offset"),
    )
    return response


@router.post("/jobs/{job_id}/cancel")
def cancel_job(job_id: str, user=Depends(verify_google_token)):
    email = user["email"].lower()
    log_stage(job_id=job_id, stage="JOB_CANCEL", event="STARTED", user=email)

    key = f"job_status:{job_id}"
    data = r.hgetall(key)

    if not data:
        log_stage(job_id=job_id, stage="JOB_CANCEL", event="FAILED", user=email, error="Job not found")
        raise HTTPException(status_code=404, detail="Job not found")

    if data.get("user") != email:
        log_stage(job_id=job_id, stage="JOB_CANCEL", event="FAILED", user=email, error="Forbidden")
        raise HTTPException(status_code=403, detail="Forbidden")

    status = (data.get("status") or "").upper()
    if status in TERMINAL_STATUSES:
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

    r.hset(
        key,
        mapping={
            "cancel_requested": "1",
            "status": JOB_STATUS_CANCELLED,
            "stage": "Cancelled by user",
            "updated_at": datetime.utcnow().isoformat(),
        },
    )

    log_stage(job_id=job_id, stage="JOB_CANCEL", event="COMPLETED", user=email, status=JOB_STATUS_CANCELLED)
    return {
        "job_id": job_id,
        "status": JOB_STATUS_CANCELLED,
        "message": "Cancellation requested",
    }
