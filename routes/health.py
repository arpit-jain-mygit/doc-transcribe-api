from fastapi import APIRouter
from utils.metrics import snapshot

router = APIRouter()


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/metrics")
def metrics():
    return {"status": "ok", "metrics": snapshot()}
