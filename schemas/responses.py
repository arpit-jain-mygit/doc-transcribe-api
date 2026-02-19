# User value: This file helps users get reliable OCR/transcription results with clear processing behavior.
from pydantic import BaseModel, Field
from typing import List, Literal, Optional


class JobCreatedResponse(BaseModel):
    # User value: confirms a job is accepted so users can confidently track processing.
    job_id: str
    status: str = "QUEUED"


class JobStatusResponse(BaseModel):
    # User value: shares live status so users know exactly where OCR/transcription stands.
    job_id: str
    status: str
    job_type: Optional[str]
    input_type: Optional[str]
    attempts: Optional[int]
    output_path: Optional[str]
    error: Optional[str]
    updated_at: Optional[str]

    # User value: summarizes OCR quality so users can trust output or decide to retry with better scans.
    ocr_quality_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    # User value: points users to specific weak pages instead of generic low-quality messaging.
    low_confidence_pages: List[int] = Field(default_factory=list)
    # User value: provides clear fix suggestions when OCR quality is weak.
    quality_hints: List[str] = Field(default_factory=list)
    # User value: summarizes transcription quality so users know when transcript review is needed.
    transcript_quality_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    # User value: identifies weak segments so users can jump directly to risky transcript sections.
    low_confidence_segments: List[int] = Field(default_factory=list)
    # User value: exposes per-segment quality details for explainable transcription outcomes.
    segment_quality: List[dict] = Field(default_factory=list)
    # User value: gives users actionable transcription-specific remediation hints.
    transcript_quality_hints: List[str] = Field(default_factory=list)


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
