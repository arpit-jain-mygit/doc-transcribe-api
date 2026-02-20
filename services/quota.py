# User value: This file helps users get reliable OCR/transcription results with clear processing behavior.
import logging
import os
from datetime import datetime

from fastapi import HTTPException

logger = logging.getLogger("api.quota")

DAILY_JOB_LIMIT_PER_USER = int(os.getenv("DAILY_JOB_LIMIT_PER_USER", "0"))
ACTIVE_JOB_LIMIT_PER_USER = int(os.getenv("ACTIVE_JOB_LIMIT_PER_USER", "0"))
MAX_OCR_PAGES = int(os.getenv("MAX_OCR_PAGES", "500"))
MAX_TRANSCRIPTION_DURATION_SEC = int(os.getenv("MAX_TRANSCRIPTION_DURATION_SEC", "0"))

_TERMINAL = {"COMPLETED", "FAILED", "CANCELLED"}


# User value: submits user files safely for OCR/transcription processing.
def enforce_upload_quotas(*, r, email: str, request_id: str, job_type: str) -> None:
    if DAILY_JOB_LIMIT_PER_USER > 0:
        day_key = datetime.utcnow().strftime("%Y%m%d")
        counter_key = f"user_daily_jobs:{email}:{day_key}"
        used = int(r.get(counter_key) or "0")
        if used >= DAILY_JOB_LIMIT_PER_USER:
            raise HTTPException(
                status_code=429,
                detail={
                    "error_code": "USER_DAILY_QUOTA_EXCEEDED",
                    "error_message": f"Daily upload limit reached ({DAILY_JOB_LIMIT_PER_USER}).",
                },
            )

    if ACTIVE_JOB_LIMIT_PER_USER > 0:
        ids = r.lrange(f"user_jobs:{email}", 0, 199) or []
        active = 0
        for jid in ids:
            status = str((r.hget(f"job_status:{jid}", "status") or "")).upper()
            if status and status not in _TERMINAL:
                active += 1
        if active >= ACTIVE_JOB_LIMIT_PER_USER:
            raise HTTPException(
                status_code=429,
                detail={
                    "error_code": "USER_ACTIVE_QUOTA_EXCEEDED",
                    "error_message": f"Active job limit reached ({ACTIVE_JOB_LIMIT_PER_USER}). Wait for completion.",
                },
            )
    logger.info(
        "quota_check_pass user=%s job_type=%s request_id=%s daily_limit=%s active_limit=%s",
        email,
        job_type,
        request_id,
        DAILY_JOB_LIMIT_PER_USER,
        ACTIVE_JOB_LIMIT_PER_USER,
    )


# User value: supports register_daily_job_usage so the OCR/transcription journey stays clear and reliable.
def register_daily_job_usage(*, r, email: str) -> None:
    if DAILY_JOB_LIMIT_PER_USER <= 0:
        return
    day_key = datetime.utcnow().strftime("%Y%m%d")
    counter_key = f"user_daily_jobs:{email}:{day_key}"
    value = int(r.incr(counter_key))
    if value == 1:
        r.expire(counter_key, 172800)


# User value: shows clear processing timing so users can set expectations.
def enforce_pages_and_duration_limits(*, job_type: str, total_pages: int | None, media_duration_sec: float | None) -> None:
    if job_type == "OCR" and MAX_OCR_PAGES > 0 and total_pages is not None and total_pages > MAX_OCR_PAGES:
        raise HTTPException(
            status_code=400,
            detail={
                "error_code": "PAGE_LIMIT_EXCEEDED",
                "error_message": f"OCR page limit exceeded ({MAX_OCR_PAGES} pages).",
            },
        )

    if (
        job_type == "TRANSCRIPTION"
        and MAX_TRANSCRIPTION_DURATION_SEC > 0
        and media_duration_sec is not None
        and media_duration_sec > float(MAX_TRANSCRIPTION_DURATION_SEC)
    ):
        raise HTTPException(
            status_code=400,
            detail={
                "error_code": "DURATION_LIMIT_EXCEEDED",
                "error_message": f"Media duration exceeds limit ({MAX_TRANSCRIPTION_DURATION_SEC}s).",
            },
        )
