# User value: This endpoint provides pre-upload route/warning/ETA guidance so users can submit files with fewer surprises.
from fastapi import APIRouter, Depends, HTTPException

from schemas.requests import IntakePrecheckRequest
from schemas.responses import IntakePrecheckResponse
from services.auth import verify_google_token
from services.feature_flags import is_smart_intake_enabled
from services.intake_eta import estimate_eta_sec
from services.intake_precheck import build_precheck_warnings
from services.intake_router import detect_route_from_metadata
from utils.request_id import get_request_id
from utils.stage_logging import log_stage

router = APIRouter()


# User value: chooses fallback route for warnings/ETA when metadata is uncertain.
def _effective_job_type(detected_job_type: str, mime_type: str | None) -> str:
    detected = str(detected_job_type or "").upper()
    if detected in {"OCR", "TRANSCRIPTION"}:
        return detected
    mime = str(mime_type or "").strip().lower()
    if mime.startswith("audio/") or mime.startswith("video/"):
        return "TRANSCRIPTION"
    return "OCR"


@router.post("/intake/precheck", response_model=IntakePrecheckResponse)
# User value: provides pre-upload routing and risk hints to reduce failed or slow OCR/transcription jobs.
async def intake_precheck(payload: IntakePrecheckRequest, user=Depends(verify_google_token)):
    if not is_smart_intake_enabled():
        raise HTTPException(
            status_code=404,
            detail={
                "error_code": "FEATURE_DISABLED",
                "error_message": "Smart Intake is disabled",
            },
        )

    request_id = get_request_id() or ""
    detected = detect_route_from_metadata(payload.filename, payload.mime_type)
    effective_job_type = _effective_job_type(detected.get("detected_job_type", "UNKNOWN"), payload.mime_type)

    warnings = build_precheck_warnings(
        job_type=effective_job_type,
        filename=payload.filename,
        mime_type=payload.mime_type,
        file_size_bytes=payload.file_size_bytes,
        media_duration_sec=payload.media_duration_sec,
        pdf_page_count=payload.pdf_page_count,
    )

    eta_sec = estimate_eta_sec(
        job_type=effective_job_type,
        file_size_bytes=payload.file_size_bytes,
        media_duration_sec=payload.media_duration_sec,
        pdf_page_count=payload.pdf_page_count,
    )

    log_stage(
        job_id="intake-precheck",
        stage="INTAKE_PRECHECK",
        event="COMPLETED",
        user=user.get("email", ""),
        request_id=request_id,
        detected_job_type=detected.get("detected_job_type", "UNKNOWN"),
        confidence=detected.get("confidence", 0.0),
        warning_count=len(warnings),
        eta_sec=eta_sec,
    )

    return IntakePrecheckResponse(
        detected_job_type=detected.get("detected_job_type", "UNKNOWN"),
        warnings=warnings,
        eta_sec=eta_sec,
        confidence=float(detected.get("confidence", 0.0)),
        reasons=list(detected.get("reasons") or []),
    )
