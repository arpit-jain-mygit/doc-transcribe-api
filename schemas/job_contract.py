CONTRACT_VERSION = "2026-02-16-prs-002"

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

CANONICAL_FIELDS = (
    "contract_version",
    "job_id",
    "job_type",
    "status",
    "stage",
    "progress",
    "source",
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
)
