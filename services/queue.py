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

QUEUE_NAME = "doc_jobs"


def enqueue_job(job_id: str, job: dict):
    key = f"job_status:{job_id}"

    # 1️⃣ Initialize job status
    r.hset(
        key,
        mapping={
            "status": "QUEUED",
            "progress": 0,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        },
    )

    # 2️⃣ Push job to queue
    payload = job.copy()
    payload["job_id"] = job_id

    r.lpush(QUEUE_NAME, json.dumps(payload))
