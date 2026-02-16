# app.py
import os
import logging

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

# Load env before importing route modules that read os.getenv at import time.
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))


def configure_logging() -> None:
    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )


configure_logging()
logger = logging.getLogger("api.error")
from startup_env import validate_startup_env

validate_startup_env()

from routes.upload import router as upload_router
from routes.status import router as status_router
from routes.health import router as health_router
from routes.auth import router as auth_router
from routes.jobs import router as jobs_router
from routes.contract import router as contract_router

app = FastAPI(title="Doc Transcribe API")



def _extract_error_message(detail) -> str:
    if isinstance(detail, dict):
        return str(detail.get("error_message") or detail.get("message") or detail.get("detail") or detail)
    if isinstance(detail, list):
        return "; ".join(str(x) for x in detail)
    return str(detail)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    detail = exc.detail
    body = {
        "error_code": f"HTTP_{exc.status_code}",
        "error_message": _extract_error_message(detail),
        "detail": detail,
        "path": request.url.path,
    }
    if isinstance(detail, dict) and detail.get("error_code"):
        body["error_code"] = str(detail.get("error_code"))
    logger.warning(
        "request_failed status=%s path=%s error_code=%s error_message=%s",
        exc.status_code,
        request.url.path,
        body["error_code"],
        body["error_message"],
    )
    return JSONResponse(status_code=exc.status_code, content=body)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    error_message = f"{exc.__class__.__name__}: {exc}"
    logger.exception("request_failed_unhandled path=%s error=%s", request.url.path, error_message)
    return JSONResponse(
        status_code=500,
        content={
            "error_code": "INTERNAL_SERVER_ERROR",
            "error_message": error_message,
            "detail": "Unhandled server exception",
            "path": request.url.path,
        },
    )


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:4200",
        "http://127.0.0.1:4200",
    ],
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(health_router)
app.include_router(contract_router)
app.include_router(upload_router)
app.include_router(status_router)
app.include_router(jobs_router)
