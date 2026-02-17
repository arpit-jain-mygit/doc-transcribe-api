# User value: This file helps users get reliable OCR/transcription results with clear processing behavior.
# routes/auth.py
from fastapi import APIRouter, HTTPException
from services.auth import verify_google_id_token

router = APIRouter()


@router.post("/auth/google")
# User value: This step keeps the user OCR/transcription flow accurate and dependable.
def google_auth(payload: dict):
    """
    Optional endpoint.
    Used only to confirm identity on frontend.
    Does NOT grant access.
    """
    token = payload.get("id_token")
    if not token:
        raise HTTPException(
            status_code=400,
            detail={"error_code": "AUTH_MISSING_TOKEN", "error_message": "Missing token"},
        )

    info = verify_google_id_token(str(token).strip())

    return {
        "email": info.get("email"),
        "name": info.get("name"),
    }
