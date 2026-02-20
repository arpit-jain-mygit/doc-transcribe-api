# User value: This file helps users get reliable OCR/transcription results with clear processing behavior.
# routes/upload.py
from fastapi import APIRouter, UploadFile, File, Form, Depends, Header

from services.auth import verify_google_token
from services.upload_orchestrator import submit_upload_job
from utils.request_id import get_request_id

router = APIRouter()


@router.post("/upload")
# User value: submits user files safely for OCR/transcription processing.
async def upload(
    file: UploadFile = File(...),
    job_type: str = Form(..., alias="type"),
    content_subtype: str | None = Form(default=None),
    idempotency_key: str | None = Header(default=None, alias="X-Idempotency-Key"),
    media_duration_sec: float | None = Header(default=None, alias="X-Media-Duration-Sec"),
    user=Depends(verify_google_token),
):
    request_id = get_request_id()
    return submit_upload_job(
        file=file,
        job_type=job_type,
        email=user["email"],
        request_id=request_id,
        idempotency_key=idempotency_key,
        media_duration_sec=media_duration_sec,
        content_subtype=content_subtype,
    )
