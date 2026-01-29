from fastapi import APIRouter
import logging
import uuid

from schemas.requests import JobRequest
from services.queue import enqueue_job

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/jobs")
def create_job(req: JobRequest):
    logger.info(
        f"Job creation request: job_type={req.job_type}, "
        f"filename={req.filename}, gcs_uri={req.gcs_uri}"
    )

    job_id = f"{req.job_type.lower()}-{uuid.uuid4().hex}"

    job = {
        "job_id": job_id,
        "job_type": req.job_type,
        "input_type": "FILE",
        "gcs_uri": req.gcs_uri,
        "filename": req.filename,
    }

    enqueue_job(job)

    logger.info(f"Job enqueued successfully: job_id={job_id}")

    return {"job_id": job_id}
