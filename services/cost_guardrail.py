# User value: This file predicts processing effort/cost so users get early warnings before expensive jobs run.
import os
from typing import Literal


PolicyDecision = Literal["ALLOW", "WARN", "BLOCK"]
EffortBand = Literal["LOW", "MEDIUM", "HIGH"]
CostBand = Literal["LOW", "MEDIUM", "HIGH", "VERY_HIGH"]

OCR_COST_PER_PAGE_USD = float(os.getenv("OCR_COST_PER_PAGE_USD", "0.02"))
OCR_COST_PER_MB_USD = float(os.getenv("OCR_COST_PER_MB_USD", "0.003"))
TRANSCRIPTION_COST_PER_MIN_USD = float(os.getenv("TRANSCRIPTION_COST_PER_MIN_USD", "0.015"))
TRANSCRIPTION_COST_PER_MB_USD = float(os.getenv("TRANSCRIPTION_COST_PER_MB_USD", "0.001"))

COST_GUARDRAIL_WARN_USD = float(os.getenv("COST_GUARDRAIL_WARN_USD", "0.75"))
COST_GUARDRAIL_BLOCK_USD = float(os.getenv("COST_GUARDRAIL_BLOCK_USD", "2.50"))


# User value: estimates job cost deterministically so users get stable guidance before upload.
def estimate_projected_cost_usd(
    *,
    job_type: str,
    file_size_bytes: int | None,
    media_duration_sec: float | None,
    pdf_page_count: int | None,
) -> float:
    jt = str(job_type or "").upper()
    size_mb = max(0.0, float(file_size_bytes or 0) / (1024 * 1024))

    if jt == "TRANSCRIPTION":
        minutes = max(0.0, float(media_duration_sec or 0) / 60.0)
        return max(0.0, (minutes * TRANSCRIPTION_COST_PER_MIN_USD) + (size_mb * TRANSCRIPTION_COST_PER_MB_USD))

    pages = max(1.0, float(pdf_page_count or 1))
    return max(0.0, (pages * OCR_COST_PER_PAGE_USD) + (size_mb * OCR_COST_PER_MB_USD))


# User value: maps projected cost to a simple effort band so users can decide quickly.
def estimate_effort_band(projected_cost_usd: float) -> EffortBand:
    cost = max(0.0, float(projected_cost_usd or 0.0))
    if cost < 0.25:
        return "LOW"
    if cost < 1.0:
        return "MEDIUM"
    return "HIGH"


# User value: maps projected cost to a readable band so users understand relative cost impact.
def estimate_cost_band(projected_cost_usd: float) -> CostBand:
    cost = max(0.0, float(projected_cost_usd or 0.0))
    if cost < 0.25:
        return "LOW"
    if cost < 1.0:
        return "MEDIUM"
    if cost < COST_GUARDRAIL_BLOCK_USD:
        return "HIGH"
    return "VERY_HIGH"


# User value: chooses allow/warn/block so users are protected from surprise expensive jobs.
def decide_policy(projected_cost_usd: float) -> tuple[PolicyDecision, str]:
    cost = max(0.0, float(projected_cost_usd or 0.0))
    if cost >= COST_GUARDRAIL_BLOCK_USD:
        return ("BLOCK", "Projected cost exceeds configured block threshold")
    if cost >= COST_GUARDRAIL_WARN_USD:
        return ("WARN", "Projected cost is high; consider splitting/compressing input")
    return ("ALLOW", "Projected cost is within safe threshold")


# User value: returns one complete cost guardrail result so API/UI can provide consistent messaging.
def evaluate_cost_guardrail(
    *,
    job_type: str,
    file_size_bytes: int | None,
    media_duration_sec: float | None,
    pdf_page_count: int | None,
) -> dict:
    projected = estimate_projected_cost_usd(
        job_type=job_type,
        file_size_bytes=file_size_bytes,
        media_duration_sec=media_duration_sec,
        pdf_page_count=pdf_page_count,
    )
    decision, reason = decide_policy(projected)
    return {
        "projected_cost_usd": round(projected, 4),
        "estimated_effort": estimate_effort_band(projected),
        "estimated_cost_band": estimate_cost_band(projected),
        "policy_decision": decision,
        "policy_reason": reason,
    }
