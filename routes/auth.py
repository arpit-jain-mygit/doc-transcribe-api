# services/auth.py
import os
import redis
from fastapi import Header, HTTPException
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

APPROVED_SET = "approved_users"
BLOCKED_SET = "blocked_users"


# =========================================================
# VERIFY + AUTHORIZE GOOGLE USER
# =========================================================
def verify_google_token(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    token = authorization.split(" ", 1)[1]

    try:
        info = id_token.verify_oauth2_token(
            token,
            requests.Request(),
            GOOGLE_CLIENT_ID,
        )
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid Google token")

    email = info.get("email")
    if not email:
        raise HTTPException(status_code=401, detail="Email not found in token")

    # -----------------------------------------------------
    # BLOCKED USER CHECK
    # -----------------------------------------------------
    if r.sismember(BLOCKED_SET, email):
        raise HTTPException(
            status_code=403,
            detail="USER_BLOCKED",
        )

    # -----------------------------------------------------
    # APPROVAL CHECK
    # -----------------------------------------------------
    if not r.sismember(APPROVED_SET, email):
        raise HTTPException(
            status_code=403,
            detail="USER_NOT_APPROVED",
        )

    return {
        "email": email,
        "user_id": info.get("sub"),
        "name": info.get("name"),
    }
