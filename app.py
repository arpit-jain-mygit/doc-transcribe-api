# app.py
import os
import logging

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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

from routes.upload import router as upload_router
from routes.status import router as status_router
from routes.health import router as health_router
from routes.auth import router as auth_router
from routes.jobs import router as jobs_router

app = FastAPI(title="Doc Transcribe API")

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
app.include_router(upload_router)
app.include_router(status_router)
app.include_router(jobs_router)
