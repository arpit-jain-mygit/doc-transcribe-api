# services/auth.py
import os
import redis
from fastapi import HTTPException, Header
from google.oauth2 import id_token
from google.auth.transport import requests

# =========================================================
# CONFIG
# =========================================================
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

if not GOOGLE_CLIENT_ID:
    raise RuntimeError("GOOGLE_CLIENT_ID not set")

r = redis.Redis.from_url(REDIS_URL, decode_responses=True)

PENDING_SET = "auth:users:pending"
APPROVED_SET = "auth:users:approved"


def verify_google_token(authorization: str = Header(None)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    token = authorization.replace("Bearer ", "")

    try:
        payload = id_token.verify_oauth2_token(
            token,
            requests.Request(),
            GOOGLE_CLIENT_ID,
        )
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid Google token")

    email = payload.get("email", "").lower()
    if not email:
        raise HTTPException(status_code=401, detail="Email not found in token")

    # --------------------------------------------------
    # APPROVAL LOGIC
    # --------------------------------------------------
    if r.sismember(APPROVED_SET, email):
        return payload

    # First-time or pending user
    r.sadd(PENDING_SET, email)

    raise HTTPException(
        status_code=403,
        detail="User pending approval",
    )
