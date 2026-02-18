# User value: This file estimates intake processing time so users can set realistic pre-upload expectations.
import math


# User value: estimates transcription ETA from media duration so users can anticipate wait time.
def _eta_for_transcription(media_duration_sec: float | None, file_size_bytes: int | None) -> int:
    if media_duration_sec is not None and media_duration_sec > 0:
        return max(15, int(math.ceil(media_duration_sec * 0.2)))

    size_mb = (float(file_size_bytes or 0) / (1024 * 1024)) if file_size_bytes is not None else 0.0
    if size_mb <= 5:
        return 45
    if size_mb <= 20:
        return 90
    return 180


# User value: estimates OCR ETA from pages/size so users can anticipate wait time.
def _eta_for_ocr(pdf_page_count: int | None, file_size_bytes: int | None) -> int:
    if pdf_page_count is not None and pdf_page_count > 0:
        return max(20, int(pdf_page_count * 20))

    size_mb = (float(file_size_bytes or 0) / (1024 * 1024)) if file_size_bytes is not None else 0.0
    if size_mb <= 2:
        return 60
    if size_mb <= 10:
        return 120
    return 240


# User value: returns a stable ETA value so UI guidance remains consistent and easy to understand.
def estimate_eta_sec(
    *,
    job_type: str,
    file_size_bytes: int | None,
    media_duration_sec: float | None,
    pdf_page_count: int | None,
) -> int:
    jt = str(job_type or "").upper()
    if jt == "TRANSCRIPTION":
        return _eta_for_transcription(media_duration_sec, file_size_bytes)
    return _eta_for_ocr(pdf_page_count, file_size_bytes)
