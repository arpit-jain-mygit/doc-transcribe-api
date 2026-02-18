# User value: This file helps users get reliable OCR/transcription results with clear processing behavior.
# app.py
import os
import logging
import time

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from utils.json_logging import configure_json_logging
from utils.metrics import incr, observe_ms

# Load env before importing route modules that read os.getenv at import time.
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))


# User value: prepares a stable OCR/transcription experience before user actions.
def configure_logging() -> None:
    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    configure_json_logging(service="doc-transcribe-api", level=level)


configure_logging()
logger = logging.getLogger("api.error")
from startup_env import validate_startup_env
from utils.request_id import REQUEST_ID_HEADER, get_request_id, normalize_request_id, set_request_id

validate_startup_env()

from routes.upload import router as upload_router
from routes.status import router as status_router
from routes.health import router as health_router
from routes.readiness import router as readiness_router
from routes.auth import router as auth_router
from routes.jobs import router as jobs_router
from routes.contract import router as contract_router
from routes.intake import router as intake_router

app = FastAPI(title="Doc Transcribe API")


# User value: normalizes data so users see consistent OCR/transcription results.
def _parse_csv_env(name: str) -> list[str]:
    raw = os.getenv(name, "")
    values = [x.strip() for x in raw.split(",") if x.strip()]
    seen = set()
    ordered = []
    for item in values:
        if item not in seen:
            seen.add(item)
            ordered.append(item)
    return ordered


@app.middleware("http")
# User value: supports request_id_middleware so the OCR/transcription journey stays clear and reliable.
async def request_id_middleware(request: Request, call_next):
    request_id = normalize_request_id(request.headers.get(REQUEST_ID_HEADER))
    set_request_id(request_id)
    started = time.perf_counter()
    status_code = 500
    try:
        response = await call_next(request)
        status_code = int(getattr(response, "status_code", 500))
        response.headers[REQUEST_ID_HEADER] = request_id
        return response
    finally:
        duration_ms = (time.perf_counter() - started) * 1000.0
        method = request.method.upper()
        path = request.url.path
        status_class = f"{status_code // 100}xx"
        incr("api_http_requests_total", method=method, path=path, status_class=status_class, status_code=status_code)
        observe_ms("api_http_request_latency_ms", duration_ms, method=method, path=path, status_class=status_class)
        set_request_id(None)


# User value: supports _extract_error_message so the OCR/transcription journey stays clear and reliable.
def _extract_error_message(detail) -> str:
    if isinstance(detail, dict):
        return str(detail.get("error_message") or detail.get("message") or detail.get("detail") or detail)
    if isinstance(detail, list):
        return "; ".join(str(x) for x in detail)
    return str(detail)


# User value: supports _to_error_code so the OCR/transcription journey stays clear and reliable.
def _to_error_code(status_code: int, detail) -> str:
    if isinstance(detail, dict) and detail.get("error_code"):
        return str(detail.get("error_code")).strip().upper()

    msg = _extract_error_message(detail).lower()
    if status_code == 401:
        if "missing authorization" in msg:
            return "AUTH_MISSING_TOKEN"
        if "invalid google token" in msg:
            return "AUTH_INVALID_TOKEN"
        if "email not found" in msg:
            return "AUTH_EMAIL_MISSING"
        if "access blocked" in msg:
            return "AUTH_USER_BLOCKED"
        return "AUTH_UNAUTHORIZED"
    if status_code == 403:
        return "AUTH_FORBIDDEN"
    if status_code == 404:
        return "RESOURCE_NOT_FOUND"
    if status_code == 409:
        return "STATE_CONFLICT"
    if status_code == 400:
        return "INVALID_REQUEST"
    return f"HTTP_{status_code}"


# User value: supports _error_body so the OCR/transcription journey stays clear and reliable.
def _error_body(*, request: Request, status_code: int, detail, error_message: str | None = None) -> dict:
    request_id = get_request_id() or normalize_request_id(request.headers.get(REQUEST_ID_HEADER))
    body = {
        "error_code": _to_error_code(status_code, detail),
        "error_message": error_message or _extract_error_message(detail),
        "detail": detail,
        "path": request.url.path,
        "request_id": request_id,
    }
    return body


@app.exception_handler(RequestValidationError)
# User value: supports validation_exception_handler so the OCR/transcription journey stays clear and reliable.
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    detail = exc.errors()
    body = _error_body(
        request=request,
        status_code=422,
        detail=detail,
        error_message="Request validation failed",
    )
    body["error_code"] = "VALIDATION_ERROR"
    logger.warning(
        "request_failed_validation status=422 path=%s request_id=%s error_code=%s",
        request.url.path,
        body["request_id"],
        body["error_code"],
    )
    return JSONResponse(status_code=422, content=body)


@app.exception_handler(StarletteHTTPException)
# User value: supports http_exception_handler so the OCR/transcription journey stays clear and reliable.
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    body = _error_body(request=request, status_code=exc.status_code, detail=exc.detail)
    logger.warning(
        "request_failed status=%s path=%s request_id=%s error_code=%s error_message=%s",
        exc.status_code,
        request.url.path,
        body["request_id"],
        body["error_code"],
        body["error_message"],
    )
    return JSONResponse(status_code=exc.status_code, content=body)


@app.exception_handler(Exception)
# User value: supports unhandled_exception_handler so the OCR/transcription journey stays clear and reliable.
async def unhandled_exception_handler(request: Request, exc: Exception):
    request_id = get_request_id() or normalize_request_id(request.headers.get(REQUEST_ID_HEADER))
    logger.exception(
        "request_failed_unhandled path=%s request_id=%s error=%s: %s",
        request.url.path,
        request_id,
        exc.__class__.__name__,
        exc,
    )
    body = _error_body(
        request=request,
        status_code=500,
        detail="Unhandled server exception",
        error_message="Internal server error",
    )
    body["error_code"] = "INTERNAL_SERVER_ERROR"
    return JSONResponse(status_code=500, content=body)


CORS_ALLOW_ORIGINS = _parse_csv_env("CORS_ALLOW_ORIGINS")
CORS_ALLOW_ORIGIN_REGEX = (os.getenv("CORS_ALLOW_ORIGIN_REGEX") or "").strip() or None
logger.info(
    "cors_configured allow_origins=%s allow_origin_regex=%s",
    CORS_ALLOW_ORIGINS,
    CORS_ALLOW_ORIGIN_REGEX or "",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOW_ORIGINS,
    allow_origin_regex=CORS_ALLOW_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=[REQUEST_ID_HEADER],
)

app.include_router(auth_router)
app.include_router(health_router)
app.include_router(readiness_router)
app.include_router(contract_router)
app.include_router(intake_router)
app.include_router(upload_router)
app.include_router(status_router)
app.include_router(jobs_router)
