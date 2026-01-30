from fastapi import APIRouter
import uuid
import json
import redis
import logging
import os

router = APIRouter()
logger = logging.getLogger(__name__)

REDIS_URL = os.environ["REDIS_URL"]
r = redis.from_url(REDIS_URL, decode_responses=True)

@router.post("/jobs")
def create_job(payload: dict):
    job_id = payload.get("job_id") or uuid.uuid4().hex

    job = {
        "job_id": job_id,
        "job_type": payload["job_type"],
        "input_type": payload["input_type"],
        "gcs_uri": payload["gcs_uri"],
        "filename": payload["filename"],
    }

    # ✅ USE job_status
    r.hset(
        f"job_status:{job_id}",
        mapping={
            "status": "QUEUED",
            "stage": "Waiting in queue",
            "progress": 0,
            "eta_sec": 0,
            "current_page": 0,
            "total_pages": 0,
            "output_uri": "",
            "error": "",
        },
    )

    r.lpush("doc_jobs", json.dumps(job))

    logger.info(f"[API] Job enqueued: {job_id}")
    return {"job_id": job_id}
