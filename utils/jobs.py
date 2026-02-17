# User value: This file helps users get reliable OCR/transcription results with clear processing behavior.
import uuid


# User value: builds the required payload/state for user OCR/transcription flow.
def create_job_id() -> str:
    return uuid.uuid4().hex
