# User value: This file helps users get reliable OCR/transcription results with clear processing behavior.
import logging
import os
from typing import List

logger = logging.getLogger("api.startup")


# User value: supports _is_blank so the OCR/transcription journey stays clear and reliable.
def _is_blank(value: str | None) -> bool:
    return value is None or not str(value).strip()


# User value: prevents invalid input so users get reliable OCR/transcription outcomes.
def _validate_redis_url(value: str | None, key: str, errors: List[str]) -> None:
    if _is_blank(value):
        errors.append(f"{key} is required")
        return
    if not (value.startswith("redis://") or value.startswith("rediss://")):
        errors.append(f"{key} must start with redis:// or rediss://")


# User value: prevents invalid input so users get reliable OCR/transcription outcomes.
def _validate_cors_allow_origins(value: str | None, errors: List[str]) -> None:
    if _is_blank(value):
        errors.append("CORS_ALLOW_ORIGINS is required")
        return

    origins = [x.strip() for x in str(value).split(",") if x.strip()]
    if not origins:
        errors.append("CORS_ALLOW_ORIGINS must contain at least one origin")
        return

    for origin in origins:
        if origin == "*":
            errors.append("CORS_ALLOW_ORIGINS must not contain '*' in strict allowlist mode")
            continue
        if not (origin.startswith("http://") or origin.startswith("https://")):
            errors.append(f"CORS origin must start with http:// or https://: {origin}")


# User value: prevents invalid input so users get reliable OCR/transcription outcomes.
def _validate_positive_int_env(name: str, default: int, errors: List[str]) -> None:
    raw = os.getenv(name)
    if _is_blank(raw):
        if default <= 0:
            errors.append(f"{name} default must be > 0")
        return
    try:
        value = int(str(raw))
    except ValueError:
        errors.append(f"{name} must be an integer")
        return
    if value <= 0:
        errors.append(f"{name} must be > 0")


# User value: prevents invalid input so users get reliable OCR/transcription outcomes.
def _validate_non_negative_int_env(name: str, default: int, errors: List[str]) -> None:
    raw = os.getenv(name)
    if _is_blank(raw):
        if default < 0:
            errors.append(f"{name} default must be >= 0")
        return
    try:
        value = int(str(raw))
    except ValueError:
        errors.append(f"{name} must be an integer")
        return
    if value < 0:
        errors.append(f"{name} must be >= 0")


# User value: prevents invalid input so users get reliable OCR/transcription outcomes.
def validate_startup_env() -> None:
    errors: List[str] = []
    warnings: List[str] = []

    required = [
        "GOOGLE_CLIENT_ID",
        "GCS_BUCKET_NAME",
        "QUEUE_NAME",
    ]
    for key in required:
        if _is_blank(os.getenv(key)):
            errors.append(f"{key} is required")

    _validate_redis_url(os.getenv("REDIS_URL"), "REDIS_URL", errors)
    _validate_cors_allow_origins(os.getenv("CORS_ALLOW_ORIGINS"), errors)
    _validate_positive_int_env("MAX_OCR_FILE_SIZE_MB", 25, errors)
    _validate_positive_int_env("MAX_TRANSCRIPTION_FILE_SIZE_MB", 100, errors)
    _validate_non_negative_int_env("MAX_OCR_PAGES", 0, errors)
    _validate_non_negative_int_env("MAX_TRANSCRIPTION_DURATION_SEC", 0, errors)
    _validate_non_negative_int_env("DAILY_JOB_LIMIT_PER_USER", 0, errors)
    _validate_non_negative_int_env("ACTIVE_JOB_LIMIT_PER_USER", 0, errors)

    if _is_blank(os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON")):
        warnings.append(
            "GOOGLE_APPLICATION_CREDENTIALS_JSON is not set; relying on ambient ADC credentials"
        )

    if errors:
        for err in errors:
            logger.error("startup_env_invalid %s", err)
        raise RuntimeError("Startup env validation failed: " + "; ".join(errors))

    for warning in warnings:
        logger.warning("startup_env_warning %s", warning)

    logger.info(
        "startup_env_validated keys=%s",
        [
            "GOOGLE_CLIENT_ID",
            "REDIS_URL",
            "QUEUE_NAME",
            "GCS_BUCKET_NAME",
            "CORS_ALLOW_ORIGINS",
            "MAX_OCR_FILE_SIZE_MB",
            "MAX_TRANSCRIPTION_FILE_SIZE_MB",
            "MAX_OCR_PAGES",
            "MAX_TRANSCRIPTION_DURATION_SEC",
            "DAILY_JOB_LIMIT_PER_USER",
            "ACTIVE_JOB_LIMIT_PER_USER",
        ],
    )
