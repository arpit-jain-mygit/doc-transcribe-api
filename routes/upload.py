from fastapi import APIRouter, UploadFile, File
import logging
import uuid
import os
import json
import redis

from services.gcs import upload_file_to_gcs

router = APIRouter()
logger = logging.getLogger(__name__)

REDIS_URL = os.environ["REDIS_URL"]
r = redis.from_url(REDIS_URL, decode_responses=True)

@router.post("/upload")
async def upload(file: UploadFile = File(...)):
    logger.info(f"Upload request received: filename={file.filename}")

    job_id = uuid.uuid4().hex
    ext = os.path.splitext(file.filename)[1]
    object_name = f"inputs/{job_id}{ext}"

    # 1️⃣ Upload to GCS
    gcs_uri = upload_file_to_gcs(file.file, object_name)

    # 2️⃣ Create job payload
    job = {
        "job_id": job_id,
        "job_type": "TRANSCRIBE" if ext.lower() != ".pdf" else "OCR",
        "input_type": "FILE",
        "gcs_uri": gcs_uri,
        "filename": file.filename,
    }

    # 3️⃣ Write initial job status (THIS WAS MISSING)
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

    # 4️⃣ Enqueue worker job
    r.lpush("doc_jobs", json.dumps(job))

    logger.info(f"[API] Job created & enqueued: {job_id}")

    return {
        "job_id": job_id,
        "gcs_uri": gcs_uri,
        "filename": file.filename,
    }
