# User value: This file decides OCR vs transcription from file metadata so users get accurate intake guidance.
import os

OCR_EXTENSIONS = {
    ".pdf", ".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff", ".bmp",
}
TRANSCRIPTION_EXTENSIONS = {
    ".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg", ".wma",
    ".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v",
}

OCR_MIME_PREFIXES = ("application/pdf", "image/")
TRANSCRIPTION_MIME_PREFIXES = ("audio/", "video/")


# User value: parses extension consistently so users get deterministic route decisions.
def _extension(filename: str | None) -> str:
    return os.path.splitext(str(filename or "").strip().lower())[1]


# User value: maps MIME to route so users get sensible routing even without extension hints.
def _route_from_mime(mime_type: str | None) -> str:
    mime = str(mime_type or "").strip().lower()
    if not mime:
        return "UNKNOWN"
    if any(mime.startswith(prefix) for prefix in OCR_MIME_PREFIXES):
        return "OCR"
    if any(mime.startswith(prefix) for prefix in TRANSCRIPTION_MIME_PREFIXES):
        return "TRANSCRIPTION"
    return "UNKNOWN"


# User value: maps extension to route so users get fast and deterministic pre-upload classification.
def _route_from_extension(filename: str | None) -> str:
    ext = _extension(filename)
    if ext in OCR_EXTENSIONS:
        return "OCR"
    if ext in TRANSCRIPTION_EXTENSIONS:
        return "TRANSCRIPTION"
    return "UNKNOWN"


# User value: returns route plus reasons so users and support teams can understand intake decisions.
def detect_route_from_metadata(filename: str | None, mime_type: str | None) -> dict:
    ext_route = _route_from_extension(filename)
    mime_route = _route_from_mime(mime_type)

    reasons: list[str] = []
    confidence = 0.0

    if ext_route != "UNKNOWN":
        detected = ext_route
        confidence = 0.95
        reasons.append(f"extension={_extension(filename) or 'none'}")
        if mime_route != "UNKNOWN":
            reasons.append(f"mime={str(mime_type or '').strip().lower()}")
            if mime_route == ext_route:
                confidence = 0.99
            else:
                confidence = 0.75
                reasons.append("mime_extension_mismatch")
        return {
            "detected_job_type": detected,
            "confidence": confidence,
            "reasons": reasons,
        }

    if mime_route != "UNKNOWN":
        return {
            "detected_job_type": mime_route,
            "confidence": 0.7,
            "reasons": [f"mime={str(mime_type or '').strip().lower()}", "extension_unknown"],
        }

    return {
        "detected_job_type": "UNKNOWN",
        "confidence": 0.0,
        "reasons": [
            f"extension={_extension(filename) or 'none'}",
            f"mime={str(mime_type or '').strip().lower() or 'none'}",
            "no_route_signal",
        ],
    }
