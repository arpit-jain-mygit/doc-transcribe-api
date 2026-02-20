# User value: This route gives users clear visibility into queue load and worker scheduling behavior.
import os
import redis
from fastapi import APIRouter, Depends

from services.auth import verify_google_token
from services.feature_flags import is_queue_orchestration_enabled

router = APIRouter()

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
r = redis.Redis.from_url(REDIS_URL, decode_responses=True)

QUEUE_MODE = str(os.getenv("QUEUE_MODE", "single")).strip().lower() or "single"
QUEUE_NAME = os.getenv("QUEUE_NAME", "doc_jobs")
LOCAL_QUEUE_NAME = os.getenv("LOCAL_QUEUE_NAME", "doc_jobs_local")
CLOUD_QUEUE_NAME = os.getenv("CLOUD_QUEUE_NAME", "doc_jobs")
OCR_QUEUE_NAME = os.getenv("QUEUE_NAME_OCR", os.getenv("OCR_QUEUE_NAME", "doc_jobs_ocr"))
TRANSCRIPTION_QUEUE_NAME = os.getenv(
    "QUEUE_NAME_TRANSCRIPTION",
    os.getenv("TRANSCRIPTION_QUEUE_NAME", "doc_jobs_transcription"),
)
WORKER_SCHEDULER_POLICY = str(os.getenv("WORKER_SCHEDULER_POLICY", "adaptive")).strip().lower() or "adaptive"
WORKER_SCHEDULER_MAX_CONSECUTIVE = int(os.getenv("WORKER_SCHEDULER_MAX_CONSECUTIVE", "2"))


# User value: returns queue names used by this deployment so UI can explain queue behavior accurately.
def queue_targets() -> list[str]:
    if QUEUE_MODE == "both":
        targets = [LOCAL_QUEUE_NAME, CLOUD_QUEUE_NAME]
    elif QUEUE_MODE == "partitioned":
        targets = [OCR_QUEUE_NAME, TRANSCRIPTION_QUEUE_NAME]
    else:
        targets = [QUEUE_NAME]

    seen = set()
    ordered = []
    for q in targets:
        if q and q not in seen:
            seen.add(q)
            ordered.append(q)
    return ordered


# User value: reads queue depth safely so queue health endpoint remains reliable under transient Redis issues.
def safe_llen(name: str) -> int:
    try:
        return int(r.llen(name) or 0)
    except Exception:
        return -1


# User value: reads inflight size safely so users can understand worker saturation.
def safe_scard(name: str) -> int:
    try:
        return int(r.scard(name) or 0)
    except Exception:
        return -1


@router.get("/queue/health")
# User value: shows queue pressure and scheduler policy while users wait in QUEUED state.
def queue_health(user=Depends(verify_google_token)):
    queues = queue_targets()
    depths = [{"name": q, "depth": safe_llen(q)} for q in queues]
    worker_clients = 0
    try:
        clients = r.client_list() or []
        worker_clients = sum(1 for c in clients if str(c.get("name") or "") == "doc-worker")
    except Exception:
        worker_clients = -1

    return {
        "enabled": is_queue_orchestration_enabled(),
        "queue_mode": QUEUE_MODE,
        "scheduler_policy": WORKER_SCHEDULER_POLICY,
        "scheduler_max_consecutive": max(1, WORKER_SCHEDULER_MAX_CONSECUTIVE),
        "worker_clients": worker_clients,
        "queues": depths,
        "inflight": {
            "OCR": safe_scard("worker:inflight:OCR"),
            "TRANSCRIPTION": safe_scard("worker:inflight:TRANSCRIPTION"),
        },
        "user": str(user.get("email") or "").lower(),
    }
