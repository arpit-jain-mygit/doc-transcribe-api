# User value: This file helps users get reliable OCR/transcription results with clear processing behavior.
from fastapi import APIRouter
from utils.metrics import snapshot

router = APIRouter()


@router.get("/health")
# User value: supports health so the OCR/transcription journey stays clear and reliable.
def health():
    return {"status": "ok"}


@router.get("/metrics")
# User value: supports metrics so the OCR/transcription journey stays clear and reliable.
def metrics():
    return {"status": "ok", "metrics": snapshot()}
