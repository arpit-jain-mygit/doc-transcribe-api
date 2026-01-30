from fastapi import APIRouter, UploadFile, File
import logging
import uuid
import os
import json
import redis

from services.gcs import upload_file_to_gcs

router = APIRouter()
logger = logging.getLogger(__name__)

REDIS_URL = os.environ.get("REDIS_URL")
if not REDIS_URL:
    raise RuntimeError("REDIS_URL not set")

r = redis.from_url(REDIS_URL, decode_responses=True)


@router.post("/upload")
async def upload(file: UploadFile = File(...)):
    logger.info(f"[API] Upload request received: filename={file.filename}")

    try:
        ext = os.path.splitext(file.filename)[1].lower()
        job_id = uuid.uuid4().hex

        object_name = f"inputs/{job_id}{ext}"
        logger.info(f"[API] Uploading to GCS: object={object_name}")

        gcs_uri = upload_file_to_gcs(file.file, object_name)

        # 🔑 CREATE JOB PAYLOAD (what worker expects)
        job = {
            "job_id": job_id,
            "job_type": "TRANSCRIBE" if ext != ".pdf" else "OCR",
            "input_type": "FILE",
            "gcs_uri": gcs_uri,
            "filename": file.filename,
        }

        # 🔑 WRITE INITIAL REDIS STATE
        r.hset(
            f"job:{job_id}",
            mapping={
                "status": "queued",
                "progress": 0,
                "output_uri": "",
                "error": "",
            },
        )

        # 🔑 ENQUEUE FOR WORKER
        r.lpush("doc_jobs", json.dumps(job))

        logger.info(f"[API] Job enqueued: job_id={job_id}")

        return {
            "job_id": job_id,
            "gcs_uri": gcs_uri,
            "filename": file.filename,
        }

    except Exception:
        logger.exception("[API] Upload failed")
        raise
