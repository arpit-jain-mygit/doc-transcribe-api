# User value: This file helps users get reliable OCR/transcription results with clear processing behavior.
import uuid


# User value: This step keeps the user OCR/transcription flow accurate and dependable.
def create_job_id() -> str:
    return uuid.uuid4().hex
