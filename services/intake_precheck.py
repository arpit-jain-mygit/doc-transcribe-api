# User value: This file generates pre-upload warnings so users can avoid slow or risky OCR/transcription submissions.
import os
from typing import List, Dict, Any

from services.intake_router import detect_route_from_metadata

MAX_OCR_FILE_SIZE_MB = int(os.getenv("MAX_OCR_FILE_SIZE_MB", "200"))
MAX_TRANSCRIPTION_FILE_SIZE_MB = int(os.getenv("MAX_TRANSCRIPTION_FILE_SIZE_MB", "100"))
MAX_OCR_PAGES = int(os.getenv("MAX_OCR_PAGES", "500"))
MAX_TRANSCRIPTION_DURATION_SEC = int(os.getenv("MAX_TRANSCRIPTION_DURATION_SEC", "0"))

WARN_RATIO = float(os.getenv("INTAKE_WARN_RATIO", "0.80"))
DEFAULT_WARN_PAGES = int(os.getenv("INTAKE_DEFAULT_WARN_PAGES", "50"))
DEFAULT_WARN_DURATION_SEC = int(os.getenv("INTAKE_DEFAULT_WARN_DURATION_SEC", "900"))


# User value: returns consistent warning payloads so users get clear and predictable guidance.
def _warn(code: str, message: str, severity: str = "WARN") -> Dict[str, str]:
    return {"code": code, "message": message, "severity": severity}


# User value: flags large uploads early so users can avoid long wait times and failures.
def _size_warnings(job_type: str, file_size_bytes: int | None) -> List[Dict[str, str]]:
    if file_size_bytes is None:
        return []

    if job_type == "OCR":
        max_bytes = MAX_OCR_FILE_SIZE_MB * 1024 * 1024
        warn_at = int(max_bytes * WARN_RATIO)
        if file_size_bytes >= warn_at:
            return [
                _warn(
                    "LARGE_FILE",
                    f"File size is high for OCR ({round(file_size_bytes / (1024 * 1024), 2)} MB). Processing may take longer.",
                )
            ]
        return []

    if job_type == "TRANSCRIPTION":
        max_bytes = MAX_TRANSCRIPTION_FILE_SIZE_MB * 1024 * 1024
        warn_at = int(max_bytes * WARN_RATIO)
        if file_size_bytes >= warn_at:
            return [
                _warn(
                    "LARGE_FILE",
                    f"File size is high for transcription ({round(file_size_bytes / (1024 * 1024), 2)} MB). Processing may take longer.",
                )
            ]

    return []


# User value: highlights lengthy media so users can set realistic completion expectations.
def _duration_warnings(job_type: str, media_duration_sec: float | None) -> List[Dict[str, str]]:
    if job_type != "TRANSCRIPTION" or media_duration_sec is None:
        return []

    warn_limit = int(MAX_TRANSCRIPTION_DURATION_SEC * WARN_RATIO) if MAX_TRANSCRIPTION_DURATION_SEC > 0 else DEFAULT_WARN_DURATION_SEC
    if media_duration_sec >= warn_limit:
        mins = int(media_duration_sec // 60)
        return [
            _warn(
                "LONG_MEDIA",
                f"Media duration is long ({mins} min). Transcription may take longer than usual.",
            )
        ]
    return []


# User value: warns on high page count so users can better estimate OCR turnaround time.
def _page_warnings(job_type: str, pdf_page_count: int | None) -> List[Dict[str, str]]:
    if job_type != "OCR" or pdf_page_count is None:
        return []

    warn_limit = int(MAX_OCR_PAGES * WARN_RATIO) if MAX_OCR_PAGES > 0 else DEFAULT_WARN_PAGES
    if pdf_page_count >= warn_limit:
        return [
            _warn(
                "HIGH_PAGE_COUNT",
                f"Page count is high ({pdf_page_count} pages). OCR may take longer.",
            )
        ]
    return []


# User value: surfaces metadata uncertainty so users can correct mismatched files before upload.
def _metadata_warnings(filename: str | None, mime_type: str | None) -> List[Dict[str, str]]:
    out = detect_route_from_metadata(filename, mime_type)
    reasons = set(out.get("reasons") or [])
    warnings: List[Dict[str, str]] = []

    if "mime_extension_mismatch" in reasons:
        warnings.append(
            _warn(
                "MIME_EXTENSION_MISMATCH",
                "Filename extension and MIME type do not match. Verify selected file type.",
            )
        )

    if "no_route_signal" in reasons:
        warnings.append(
            _warn(
                "UNCERTAIN_FILE_TYPE",
                "Could not confidently detect file type from filename and MIME.",
            )
        )

    return warnings


# User value: composes all warning checks so users receive complete pre-upload guidance in one response.
def build_precheck_warnings(
    *,
    job_type: str,
    filename: str | None,
    mime_type: str | None,
    file_size_bytes: int | None,
    media_duration_sec: float | None,
    pdf_page_count: int | None,
) -> List[Dict[str, Any]]:
    warnings: List[Dict[str, Any]] = []
    warnings.extend(_size_warnings(job_type, file_size_bytes))
    warnings.extend(_duration_warnings(job_type, media_duration_sec))
    warnings.extend(_page_warnings(job_type, pdf_page_count))
    warnings.extend(_metadata_warnings(filename, mime_type))
    return warnings
