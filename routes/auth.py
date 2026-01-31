from fastapi import APIRouter, HTTPException
from google.oauth2 import id_token
from google.auth.transport import requests
import os

router = APIRouter()

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")

@router.post("/auth/google")
def google_auth(payload: dict):
    token = payload.get("id_token")
    if not token:
        raise HTTPException(400, "Missing token")

    try:
        info = id_token.verify_oauth2_token(
            token,
            requests.Request(),
            GOOGLE_CLIENT_ID
        )
    except Exception:
        raise HTTPException(401, "Invalid token")

    return {
        "user_id": info["sub"],
        "email": info["email"],
        "name": info.get("name"),
    }
