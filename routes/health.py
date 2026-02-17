# User value: This file helps users get reliable OCR/transcription results with clear processing behavior.
from fastapi import APIRouter
from utils.metrics import snapshot

router = APIRouter()


@router.get("/health")
# User value: This step keeps the user OCR/transcription flow accurate and dependable.
def health():
    return {"status": "ok"}


@router.get("/metrics")
# User value: This step keeps the user OCR/transcription flow accurate and dependable.
def metrics():
    return {"status": "ok", "metrics": snapshot()}
