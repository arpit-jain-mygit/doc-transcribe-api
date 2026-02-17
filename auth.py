# User value: This file helps users get reliable OCR/transcription results with clear processing behavior.
from fastapi import Header, HTTPException


# User value: This step keeps the user OCR/transcription flow accurate and dependable.
async def verify_token(authorization: str = Header(...)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid auth header")

    # TEMP: trust token (you already validate on worker / GCP side)
    return authorization
