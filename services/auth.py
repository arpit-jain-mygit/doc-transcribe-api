# services/auth.py
import os
import redis
from fastapi import HTTPException, Header
from google.oauth2 import id_token
from google.auth.transport import requests

# -----------------------------------------------------------------------------
# Config
# -----------------------------------------------------------------------------

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

if not GOOGLE_CLIENT_ID:
    raise RuntimeError("GOOGLE_CLIENT_ID not set")

r = redis.Redis.from_url(REDIS_URL, decode_responses=True)

# -----------------------------------------------------------------------------
# Redis Keys
# -----------------------------------------------------------------------------

BLOCKED_SET = "auth:users:blocked"

# -----------------------------------------------------------------------------
# Auth Logic (DEFAULT ALLOW)
# -----------------------------------------------------------------------------

def verify_google_token(authorization: str = Header(None)) -> dict:
    """
    Verifies Google ID token.
    Access is ALLOWED by default.
    Only explicitly blocked users are denied.
    """

    # -------------------------------------------------------------------------
    # Validate Authorization Header
    # -------------------------------------------------------------------------
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    token = authorization.replace("Bearer ", "").strip()

    # -------------------------------------------------------------------------
    # Verify Google Token
    # -------------------------------------------------------------------------
    try:
        payload = id_token.verify_oauth2_token(
            token,
            requests.Request(),
            GOOGLE_CLIENT_ID,
        )
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid Google token")

    email = payload.get("email")
    if not email:
        raise HTTPException(status_code=401, detail="Email not found in token")

    email = email.lower()

    # -------------------------------------------------------------------------
    # Blocklist check (ONLY restriction)
    # -------------------------------------------------------------------------
    if r.sismember(BLOCKED_SET, email):
        raise HTTPException(
            status_code=403,
            detail="User access blocked",
        )

    # -------------------------------------------------------------------------
    # Default allow
    # -------------------------------------------------------------------------
    return payload
