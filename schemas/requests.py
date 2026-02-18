# User value: This file helps users get reliable OCR/transcription results with clear processing behavior.
from pydantic import BaseModel, Field
from typing import Literal, Optional

class JobRequest(BaseModel):
    job_type: Literal["TRANSCRIBE", "OCR"]
    input_type: Literal["FILE"]
    gcs_uri: str
    filename: str


class IntakePrecheckRequest(BaseModel):
    # User value: This captures file metadata so users get pre-upload routing and guidance.
    filename: str = Field(..., min_length=1)
    mime_type: Optional[str] = None
    file_size_bytes: Optional[int] = Field(default=None, ge=0)
    media_duration_sec: Optional[float] = Field(default=None, ge=0)
    pdf_page_count: Optional[int] = Field(default=None, ge=1)
