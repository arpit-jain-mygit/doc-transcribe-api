import os


def _flag(name: str, default: bool = False) -> bool:
    raw = str(os.getenv(name, "1" if default else "0")).strip().lower()
    return raw in {"1", "true", "yes", "on"}


FEATURE_QUEUE_PARTITIONING = _flag("FEATURE_QUEUE_PARTITIONING", False)
FEATURE_UPLOAD_QUOTAS = _flag("FEATURE_UPLOAD_QUOTAS", False)
FEATURE_DURATION_PAGE_LIMITS = _flag("FEATURE_DURATION_PAGE_LIMITS", False)
