# User value: This file helps users get reliable OCR/transcription results with clear processing behavior.
import redis
import os
import json
from datetime import datetime

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# 🔑 SINGLE CLIENT INSTANCE
r = redis.Redis.from_url(
    REDIS_URL,
    decode_responses=True,
    socket_keepalive=True,
    socket_connect_timeout=2,
    retry_on_timeout=True,
)

QUEUE_NAME = os.getenv("QUEUE_NAME", "doc_jobs")


# User value: routes work so user OCR/transcription jobs are processed correctly.
def enqueue_job(job_id: str, job: dict):
    payload = job.copy()
    payload["job_id"] = job_id

    r.lpush(QUEUE_NAME, json.dumps(payload))
