# User value: This file helps users get reliable OCR/transcription results with clear processing behavior.
from fastapi import APIRouter

from schemas.job_contract import (
    CONTRACT_VERSION,
    JOB_TYPES,
    JOB_STATUSES,
    TERMINAL_STATUSES,
    CANONICAL_FIELDS,
)
from services.feature_flags import (
    is_cost_guardrail_enabled,
    is_queue_orchestration_enabled,
    is_smart_intake_enabled,
)

router = APIRouter()


@router.get("/contract/job-status")
# User value: keeps job/status fields consistent across OCR/transcription views.
def job_status_contract():
    return {
        "contract_version": CONTRACT_VERSION,
        "job_types": list(JOB_TYPES),
        "job_statuses": list(JOB_STATUSES),
        "terminal_statuses": list(TERMINAL_STATUSES),
        "canonical_fields": list(CANONICAL_FIELDS),
        "capabilities": {
            "smart_intake_enabled": is_smart_intake_enabled(),
            "cost_guardrail_enabled": is_cost_guardrail_enabled(),
            "queue_orchestration_enabled": is_queue_orchestration_enabled(),
        },
    }
