# User value: This file helps users get reliable OCR/transcription results with clear processing behavior.
import re
import uuid
from contextvars import ContextVar

REQUEST_ID_HEADER = "X-Request-ID"
_REQUEST_ID_CTX: ContextVar[str | None] = ContextVar("request_id", default=None)
_REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9._:-]{8,128}$")


# User value: normalizes data so users see consistent OCR/transcription results.
def normalize_request_id(raw: str | None) -> str:
    value = (raw or "").strip()
    if value and _REQUEST_ID_RE.match(value):
        return value
    return f"req-{uuid.uuid4().hex}"


# User value: updates user-visible OCR/transcription state accurately.
def set_request_id(value: str | None) -> None:
    _REQUEST_ID_CTX.set(value)


# User value: loads latest OCR/transcription data so users see current status.
def get_request_id() -> str | None:
    return _REQUEST_ID_CTX.get()
