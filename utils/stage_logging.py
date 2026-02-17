# User value: This file helps users get reliable OCR/transcription results with clear processing behavior.
import logging
from datetime import datetime, timezone
from typing import Any

from utils.request_id import get_request_id

logger = logging.getLogger("api.stage")


# User value: This step keeps the user OCR/transcription flow accurate and dependable.
def _norm(value: Any) -> Any:
    if isinstance(value, bool):
        return value
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str):
        return value
    return str(value)


# User value: This step keeps the user OCR/transcription flow accurate and dependable.
def log_stage(
    *,
    job_id: str,
    stage: str,
    event: str,
    user: str | None = None,
    job_type: str | None = None,
    source: str | None = None,
    error: str | None = None,
    **extra: Any,
) -> None:
    request_id = str(extra.pop("request_id", "") or get_request_id() or "").strip()
    payload = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "job_id": job_id,
        "stage": stage,
        "event": event.upper(),
    }

    if user:
        payload["user"] = user
    if job_type:
        payload["job_type"] = job_type
    if source:
        payload["source"] = source
    if error:
        payload["error"] = error
    if request_id:
        payload["request_id"] = request_id

    for key, value in extra.items():
        norm = _norm(value)
        if norm is not None:
            payload[key] = norm

    if error or payload["event"] == "FAILED":
        logger.error("stage_event", extra={"payload": payload})
    else:
        logger.info("stage_event", extra={"payload": payload})
