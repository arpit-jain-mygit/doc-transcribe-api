import logging
import os
from typing import List

logger = logging.getLogger("api.startup")


def _is_blank(value: str | None) -> bool:
    return value is None or not str(value).strip()


def _validate_redis_url(value: str | None, key: str, errors: List[str]) -> None:
    if _is_blank(value):
        errors.append(f"{key} is required")
        return
    if not (value.startswith("redis://") or value.startswith("rediss://")):
        errors.append(f"{key} must start with redis:// or rediss://")


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

    logger.info("startup_env_validated keys=%s", ["GOOGLE_CLIENT_ID", "REDIS_URL", "QUEUE_NAME", "GCS_BUCKET_NAME"])
