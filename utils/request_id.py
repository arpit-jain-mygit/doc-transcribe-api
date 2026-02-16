import re
import uuid
from contextvars import ContextVar

REQUEST_ID_HEADER = "X-Request-ID"
_REQUEST_ID_CTX: ContextVar[str | None] = ContextVar("request_id", default=None)
_REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9._:-]{8,128}$")


def normalize_request_id(raw: str | None) -> str:
    value = (raw or "").strip()
    if value and _REQUEST_ID_RE.match(value):
        return value
    return f"req-{uuid.uuid4().hex}"


def set_request_id(value: str | None) -> None:
    _REQUEST_ID_CTX.set(value)


def get_request_id() -> str | None:
    return _REQUEST_ID_CTX.get()
