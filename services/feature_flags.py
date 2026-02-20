# User value: This file helps users get reliable OCR/transcription results with clear processing behavior.
import os


# User value: supports _flag so the OCR/transcription journey stays clear and reliable.
def _flag(name: str, default: bool = False) -> bool:
    raw = str(os.getenv(name, "1" if default else "0")).strip().lower()
    return raw in {"1", "true", "yes", "on"}


FEATURE_QUEUE_PARTITIONING = _flag("FEATURE_QUEUE_PARTITIONING", False)
FEATURE_UPLOAD_QUOTAS = _flag("FEATURE_UPLOAD_QUOTAS", False)
FEATURE_DURATION_PAGE_LIMITS = _flag("FEATURE_DURATION_PAGE_LIMITS", False)
FEATURE_SMART_INTAKE = _flag("FEATURE_SMART_INTAKE", False)
FEATURE_COST_GUARDRAIL = _flag("FEATURE_COST_GUARDRAIL", True)
FEATURE_QUEUE_ORCHESTRATION = _flag("FEATURE_QUEUE_ORCHESTRATION", True)


# User value: supports is_smart_intake_enabled so users only see intake agent behavior when it is safely enabled.
def is_smart_intake_enabled() -> bool:
    return FEATURE_SMART_INTAKE


# User value: supports is_cost_guardrail_enabled so users get predictable cost checks during intake/upload.
def is_cost_guardrail_enabled() -> bool:
    return FEATURE_COST_GUARDRAIL


# User value: supports queue orchestration visibility so users can trust queued-job behavior.
def is_queue_orchestration_enabled() -> bool:
    return FEATURE_QUEUE_ORCHESTRATION
