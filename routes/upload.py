# routes/upload.py
from fastapi import APIRouter, UploadFile, File, Form, Depends, Header

from services.auth import verify_google_token
from services.upload_orchestrator import submit_upload_job
from utils.request_id import get_request_id

router = APIRouter()


@router.post("/upload")
async def upload(
    file: UploadFile = File(...),
    job_type: str = Form(..., alias="type"),
    idempotency_key: str | None = Header(default=None, alias="X-Idempotency-Key"),
    user=Depends(verify_google_token),
):
    request_id = get_request_id()
    return submit_upload_job(
        file=file,
        job_type=job_type,
        email=user["email"],
        request_id=request_id,
        idempotency_key=idempotency_key,
    )
