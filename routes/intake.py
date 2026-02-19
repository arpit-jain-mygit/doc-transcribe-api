# User value: This endpoint provides pre-upload route/warning/ETA guidance so users can submit files with fewer surprises.
from fastapi import APIRouter, Depends, HTTPException

from schemas.requests import IntakePrecheckRequest
from schemas.responses import IntakePrecheckResponse
from services.auth import verify_google_token
from services.cost_guardrail import evaluate_cost_guardrail
from services.feature_flags import is_cost_guardrail_enabled, is_smart_intake_enabled
from services.intake_eta import estimate_eta_sec
from services.intake_precheck import build_precheck_warnings
from services.intake_router import detect_route_from_metadata
from utils.metrics import incr
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


# User value: groups ETA into stable buckets so operators can track user wait trends.
def _eta_bucket(eta_sec: int) -> str:
    eta = int(max(0, eta_sec or 0))
    if eta <= 30:
        return "lte_30s"
    if eta <= 120:
        return "31_120s"
    if eta <= 300:
        return "121_300s"
    return "gt_300s"


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
    detected_job_type = str(detected.get("detected_job_type", "UNKNOWN") or "UNKNOWN")
    effective_job_type = _effective_job_type(detected_job_type, payload.mime_type)

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
    cost = (
        evaluate_cost_guardrail(
            job_type=effective_job_type,
            file_size_bytes=payload.file_size_bytes,
            media_duration_sec=payload.media_duration_sec,
            pdf_page_count=payload.pdf_page_count,
        )
        if is_cost_guardrail_enabled()
        else {
            "estimated_effort": "LOW",
            "estimated_cost_band": "LOW",
            "policy_decision": "ALLOW",
            "policy_reason": "Cost guardrail is disabled",
            "projected_cost_usd": 0.0,
        }
    )

    confidence = float(detected.get("confidence", 0.0))
    route = detected_job_type.upper()

    log_stage(
        job_id="intake-precheck",
        stage="INTAKE_PRECHECK_DECISION",
        event="COMPLETED",
        user=user.get("email", ""),
        request_id=request_id,
        detected_job_type=detected_job_type,
        route=route,
        confidence=confidence,
        warning_count=len(warnings),
        eta_sec=eta_sec,
        eta_bucket=_eta_bucket(eta_sec),
        policy_decision=cost.get("policy_decision", "ALLOW"),
        estimated_cost_band=cost.get("estimated_cost_band", "LOW"),
        projected_cost_usd=cost.get("projected_cost_usd", 0.0),
    )

    incr("intake.precheck.decisions_total", route=route, job_type=effective_job_type)
    incr("intake.precheck.warnings_total", amount=len(warnings), route=route, job_type=effective_job_type)
    incr("intake.precheck.eta_bucket_total", bucket=_eta_bucket(eta_sec), route=route, job_type=effective_job_type)

    return IntakePrecheckResponse(
        detected_job_type=detected_job_type,
        warnings=warnings,
        eta_sec=eta_sec,
        confidence=confidence,
        reasons=list(detected.get("reasons") or []),
        estimated_effort=cost.get("estimated_effort", "LOW"),
        estimated_cost_band=cost.get("estimated_cost_band", "LOW"),
        policy_decision=cost.get("policy_decision", "ALLOW"),
        policy_reason=cost.get("policy_reason", ""),
        projected_cost_usd=cost.get("projected_cost_usd", 0.0),
    )
