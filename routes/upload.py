from fastapi import APIRouter, UploadFile, File
import logging
import uuid
import os

from services.gcs import upload_file_to_gcs

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/upload")
async def upload(file: UploadFile = File(...)):
    logger.info(f"Upload request received: filename={file.filename}")

    try:
        ext = os.path.splitext(file.filename)[1]
        object_name = f"inputs/{uuid.uuid4().hex}{ext}"

        logger.info(f"Uploading to GCS: object={object_name}")

        gcs_uri = upload_file_to_gcs(file.file, object_name)

        logger.info(f"Upload successful: gcs_uri={gcs_uri}")

        return {
            "gcs_uri": gcs_uri,
            "filename": file.filename
        }

    except Exception:
        logger.exception("Upload failed")
        raise
