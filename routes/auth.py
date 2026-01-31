# routes/auth.py
from fastapi import APIRouter, HTTPException
from google.oauth2 import id_token
from google.auth.transport import requests
import os

router = APIRouter()

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")

if not GOOGLE_CLIENT_ID:
    raise RuntimeError("GOOGLE_CLIENT_ID not set")


@router.post("/auth/google")
def google_auth(payload: dict):
    """
    Optional endpoint.
    Used only to verify token from frontend (debug / UI confirmation).
    NOT used for authorization (that happens via Depends).
    """
    token = payload.get("id_token")
    if not token:
        raise HTTPException(status_code=400, detail="Missing token")

    try:
        info = id_token.verify_oauth2_token(
            token,
            requests.Request(),
            GOOGLE_CLIENT_ID,
        )
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid Google token")

    return {
        "user_id": info.get("sub"),
        "email": info.get("email"),
        "name": info.get("name"),
    }
