import json
import time
import logging
from datetime import datetime

from redis_client import redis_client

logger = logging.getLogger("api.upload")

QUEUE_NAME = "doc_jobs"

async def upload_file(job, job_id, email, type):
    """
    This function wraps your existing upload logic.
    ONLY LOGS are added.
    """

    logger.info(f"[UPLOAD] Starting upload job_id={job_id} user={email}")

    # -----------------------------------------------------
    # JOB STATUS INIT
    # -----------------------------------------------------
    redis_client.hset(
        f"job_status:{job_id}",
        mapping={
            "status": "QUEUED",
            "stage": "Queued",
            "progress": 0,
            "user": email,
            "job_type": type,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        },
    )

    logger.info(f"[UPLOAD] Job status initialized job_id={job_id}")

    # -----------------------------------------------------
    # ENQUEUE JOB
    # -----------------------------------------------------
    logger.info(f"[UPLOAD] Enqueuing job_id={job_id}")

    redis_client.lpush(QUEUE_NAME, json.dumps(job))

    # -----------------------------------------------------
    # QUEUE DEPTH CONFIRMATION
    # -----------------------------------------------------
    try:
        depth = redis_client.llen(QUEUE_NAME)
        logger.info(
            f"[UPLOAD] Job enqueued job_id={job_id} queue_depth={depth}"
        )
    except Exception as e:
        logger.error(
            f"[UPLOAD] Failed to read queue depth job_id={job_id}: {e}"
        )

    # -----------------------------------------------------
    # REDIS HEALTH AFTER ENQUEUE
    # -----------------------------------------------------
    try:
        t0 = time.time()
        redis_client.ping()
        ms = int((time.time() - t0) * 1000)
        logger.info(
            f"[UPLOAD] Redis ping OK after enqueue latency={ms}ms"
        )
    except Exception as e:
        logger.error(
            f"[UPLOAD] Redis ping FAILED after enqueue job_id={job_id}: {e}"
        )

    logger.info(f"[UPLOAD] Upload flow finished job_id={job_id}")
