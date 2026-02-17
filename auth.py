# User value: This file helps users get reliable OCR/transcription results with clear processing behavior.
from fastapi import Header, HTTPException


# User value: supports verify_token so the OCR/transcription journey stays clear and reliable.
async def verify_token(authorization: str = Header(...)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid auth header")

    # TEMP: trust token (you already validate on worker / GCP side)
    return authorization
