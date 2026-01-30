from fastapi import APIRouter, UploadFile, File
import logging
import uuid
import os

from services.gcs import upload_file_to_gcs
from services.jobs import create_job

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/upload")
async def upload(file: UploadFile = File(...)):
    logger.info(f"Upload request received: filename={file.filename}")

    ext = os.path.splitext(file.filename)[1]
    job_id = uuid.uuid4().hex
    object_name = f"inputs/{job_id}{ext}"

    logger.info(f"Uploading to GCS: object={object_name}")

    gcs_uri = upload_file_to_gcs(file.file, object_name)

    job = create_job(job_id, gcs_uri)

    logger.info(f"Job created: job_id={job_id}")

    return job
