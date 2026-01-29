from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from routes import jobs, status, dlq, health, upload

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [API] %(levelname)s %(message)s",
)

logger = logging.getLogger(__name__)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://doc-transcribe.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload.router)
app.include_router(jobs.router)
app.include_router(status.router)
app.include_router(dlq.router)
app.include_router(health.router)
