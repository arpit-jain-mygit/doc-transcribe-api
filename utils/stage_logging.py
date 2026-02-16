import json
import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("api.stage")


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

    for key, value in extra.items():
        norm = _norm(value)
        if norm is not None:
            payload[key] = norm

    msg = json.dumps(payload, ensure_ascii=False)
    if error or payload["event"] == "FAILED":
        logger.error("stage_event %s", msg)
    else:
        logger.info("stage_event %s", msg)
