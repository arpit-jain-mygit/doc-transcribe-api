# User value: This file helps users get reliable OCR/transcription results with clear processing behavior.
from fastapi import APIRouter

from schemas.job_contract import (
    CONTRACT_VERSION,
    JOB_TYPES,
    JOB_STATUSES,
    TERMINAL_STATUSES,
    CANONICAL_FIELDS,
)

router = APIRouter()


@router.get("/contract/job-status")
# User value: This step keeps the user OCR/transcription flow accurate and dependable.
def job_status_contract():
    return {
        "contract_version": CONTRACT_VERSION,
        "job_types": list(JOB_TYPES),
        "job_statuses": list(JOB_STATUSES),
        "terminal_statuses": list(TERMINAL_STATUSES),
        "canonical_fields": list(CANONICAL_FIELDS),
    }
