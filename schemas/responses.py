# User value: This file helps users get reliable OCR/transcription results with clear processing behavior.
from pydantic import BaseModel, Field
from typing import List, Literal, Optional

class JobCreatedResponse(BaseModel):
    job_id: str
    status: str = "QUEUED"


class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    job_type: Optional[str]
    input_type: Optional[str]
    attempts: Optional[int]
    output_path: Optional[str]
    error: Optional[str]
    updated_at: Optional[str]


class IntakeWarning(BaseModel):
    # User value: This gives users clear warnings before uploading expensive/problematic files.
    code: str
    message: str
    severity: Literal["INFO", "WARN"]


class IntakePrecheckResponse(BaseModel):
    # User value: This helps users decide with route, ETA, confidence, and reasons before upload.
    detected_job_type: Literal["OCR", "TRANSCRIPTION", "UNKNOWN"]
    warnings: List[IntakeWarning] = Field(default_factory=list)
    eta_sec: Optional[int] = Field(default=None, ge=0)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    reasons: List[str] = Field(default_factory=list)
