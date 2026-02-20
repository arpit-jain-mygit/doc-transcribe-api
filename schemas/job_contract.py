# User value: This file helps users get reliable OCR/transcription results with clear processing behavior.
CONTRACT_VERSION = "2026-02-16-prs-041"

JOB_TYPES = ("OCR", "TRANSCRIPTION")

JOB_STATUS_QUEUED = "QUEUED"
JOB_STATUS_PROCESSING = "PROCESSING"
JOB_STATUS_COMPLETED = "COMPLETED"
JOB_STATUS_FAILED = "FAILED"
JOB_STATUS_CANCELLED = "CANCELLED"

JOB_STATUSES = (
    JOB_STATUS_QUEUED,
    JOB_STATUS_PROCESSING,
    JOB_STATUS_COMPLETED,
    JOB_STATUS_FAILED,
    JOB_STATUS_CANCELLED,
)

TERMINAL_STATUSES = (
    JOB_STATUS_COMPLETED,
    JOB_STATUS_FAILED,
    JOB_STATUS_CANCELLED,
)

TRACKED_HISTORY_STATUSES = (
    JOB_STATUS_COMPLETED,
    JOB_STATUS_FAILED,
    JOB_STATUS_CANCELLED,
)

INTAKE_PRECHECK_FIELDS = (
    "detected_job_type",
    "warnings",
    "eta_sec",
    "confidence",
    "reasons",
    "estimated_effort",
    "estimated_cost_band",
    "policy_decision",
    "policy_reason",
    "projected_cost_usd",
)

OCR_QUALITY_FIELDS = (
    "ocr_quality_score",
    "low_confidence_pages",
    "quality_hints",
)

TRANSCRIPTION_QUALITY_FIELDS = (
    "transcript_quality_score",
    "low_confidence_segments",
    "segment_quality",
    "transcript_quality_hints",
)

RECOVERY_FIELDS = (
    "recovery_action",
    "recovery_reason",
    "recovery_attempt",
    "recovery_max_attempts",
    "recovery_trace",
)

ASSIST_FIELDS = (
    "assist",
)

CANONICAL_FIELDS = (
    "contract_version",
    "request_id",
    "job_id",
    "job_type",
    "status",
    "stage",
    "progress",
    "source",
    "content_subtype",
    "input_filename",
    "input_size_bytes",
    "output_filename",
    "output_path",
    "download_url",
    "duration_sec",
    "total_pages",
    "error",
    "cancel_requested",
    "created_at",
    "updated_at",
    *INTAKE_PRECHECK_FIELDS,
    *OCR_QUALITY_FIELDS,
    *TRANSCRIPTION_QUALITY_FIELDS,
    *RECOVERY_FIELDS,
    *ASSIST_FIELDS,
)
