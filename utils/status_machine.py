# User value: This file helps users get reliable OCR/transcription results with clear processing behavior.
import logging
from typing import Optional

from schemas.job_contract import (
    JOB_STATUS_QUEUED,
    JOB_STATUS_PROCESSING,
    JOB_STATUS_COMPLETED,
    JOB_STATUS_FAILED,
    JOB_STATUS_CANCELLED,
)

logger = logging.getLogger("api.status_machine")

_TERMINAL = {JOB_STATUS_COMPLETED, JOB_STATUS_FAILED, JOB_STATUS_CANCELLED}

_ALLOWED = {
    None: {
        JOB_STATUS_QUEUED,
        JOB_STATUS_PROCESSING,
        JOB_STATUS_COMPLETED,
        JOB_STATUS_FAILED,
        JOB_STATUS_CANCELLED,
    },
    JOB_STATUS_QUEUED: {
        JOB_STATUS_QUEUED,
        JOB_STATUS_PROCESSING,
        JOB_STATUS_COMPLETED,
        JOB_STATUS_FAILED,
        JOB_STATUS_CANCELLED,
    },
    JOB_STATUS_PROCESSING: {
        JOB_STATUS_PROCESSING,
        JOB_STATUS_COMPLETED,
        JOB_STATUS_FAILED,
        JOB_STATUS_CANCELLED,
    },
    JOB_STATUS_COMPLETED: {JOB_STATUS_COMPLETED},
    JOB_STATUS_FAILED: {JOB_STATUS_FAILED},
    JOB_STATUS_CANCELLED: {JOB_STATUS_CANCELLED},
}


# User value: This step keeps the user OCR/transcription flow accurate and dependable.
def _norm(status: Optional[str]) -> Optional[str]:
    if status is None:
        return None
    s = str(status).strip().upper()
    return s or None


# User value: This step keeps the user OCR/transcription flow accurate and dependable.
def is_allowed_transition(current: Optional[str], target: Optional[str]) -> bool:
    target_n = _norm(target)
    if not target_n:
        return True
    current_n = _norm(current)
    allowed = _ALLOWED.get(current_n, _ALLOWED[None])
    return target_n in allowed


# User value: This step keeps the user OCR/transcription flow accurate and dependable.
def transition_hset(r, *, key: str, mapping: dict, context: str, request_id: str = "") -> tuple[bool, Optional[str], Optional[str]]:
    target = _norm(mapping.get("status"))
    if not target:
        r.hset(key, mapping=mapping)
        return True, None, None

    current_data = r.hgetall(key) or {}
    current = _norm(current_data.get("status"))

    if not is_allowed_transition(current, target):
        logger.warning(
            "status_transition_blocked context=%s key=%s current=%s target=%s request_id=%s",
            context,
            key,
            current,
            target,
            request_id,
        )
        return False, current, target

    r.hset(key, mapping=mapping)

    if current and current in _TERMINAL and current == target:
        logger.info(
            "status_transition_idempotent_terminal context=%s key=%s status=%s request_id=%s",
            context,
            key,
            target,
            request_id,
        )

    return True, current, target
