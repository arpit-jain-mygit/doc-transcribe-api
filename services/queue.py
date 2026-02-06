import json
import queue
from datetime import datetime

import redis

QUEUE_NAME = "doc_jobs"


def enqueue_job(job_id: str, job: dict):
    payload = {
        "job_id": job_id,
        **job,
    }

    redis.hset(
        f"job_status:{job_id}",
        mapping={
            "status": "QUEUED",
            "progress": 0,
            "stage": "Queued",
            "updated_at": datetime.utcnow().isoformat(),
        },
    )

    redis.lpush("doc_jobs", json.dumps(payload))


