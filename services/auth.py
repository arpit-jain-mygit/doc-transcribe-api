# services/auth.py
import os
import time
import redis
from redis.exceptions import RedisError
from fastapi import HTTPException, Header
from google.oauth2 import id_token
from google.auth.transport import requests

# -----------------------------------------------------------------------------
# Config
# -----------------------------------------------------------------------------

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
TOKEN_CLOCK_SKEW_SEC = int(os.getenv("TOKEN_CLOCK_SKEW_SEC", "60"))
ALLOWED_ISSUERS = {
    "https://accounts.google.com",
    "accounts.google.com",
}

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

def _unauthorized(error_code: str, message: str) -> HTTPException:
    return HTTPException(status_code=401, detail={"error_code": error_code, "error_message": message})


def _forbidden(error_code: str, message: str) -> HTTPException:
    return HTTPException(status_code=403, detail={"error_code": error_code, "error_message": message})


def verify_google_id_token(token: str) -> dict:
    if not token:
        raise _unauthorized("AUTH_MISSING_TOKEN", "Missing token")

    try:
        payload = id_token.verify_oauth2_token(
            token,
            requests.Request(),
            GOOGLE_CLIENT_ID,
        )
    except Exception:
        raise _unauthorized("AUTH_INVALID_TOKEN", "Invalid Google token")

    issuer = str(payload.get("iss") or "").strip()
    if issuer not in ALLOWED_ISSUERS:
        raise _unauthorized("AUTH_INVALID_ISSUER", "Invalid token issuer")

    audience = str(payload.get("aud") or "").strip()
    if audience != GOOGLE_CLIENT_ID:
        raise _unauthorized("AUTH_INVALID_AUDIENCE", "Invalid token audience")

    authorized_party = str(payload.get("azp") or "").strip()
    if authorized_party and authorized_party != GOOGLE_CLIENT_ID:
        raise _unauthorized("AUTH_INVALID_AUTHORIZED_PARTY", "Invalid token authorized party")

    now = int(time.time())
    exp = int(payload.get("exp") or 0)
    if exp <= now - TOKEN_CLOCK_SKEW_SEC:
        raise _unauthorized("AUTH_TOKEN_EXPIRED", "Token expired")

    nbf = int(payload.get("nbf") or 0)
    if nbf and nbf > now + TOKEN_CLOCK_SKEW_SEC:
        raise _unauthorized("AUTH_TOKEN_NOT_YET_VALID", "Token not valid yet")

    iat = int(payload.get("iat") or 0)
    if iat and iat > now + TOKEN_CLOCK_SKEW_SEC:
        raise _unauthorized("AUTH_TOKEN_ISSUED_IN_FUTURE", "Token issue time is invalid")

    email = payload.get("email")
    if not email:
        raise _unauthorized("AUTH_EMAIL_MISSING", "Email not found in token")

    if payload.get("email_verified") is not True:
        raise _unauthorized("AUTH_EMAIL_NOT_VERIFIED", "Email is not verified")

    email = email.lower()

    # -------------------------------------------------------------------------
    # Blocklist check (ONLY restriction)
    # -------------------------------------------------------------------------
    try:
        if r.sismember(BLOCKED_SET, email):
            raise _forbidden("AUTH_USER_BLOCKED", "User access blocked")
    except RedisError:
        raise HTTPException(
            status_code=503,
            detail={
                "error_code": "INFRA_REDIS",
                "error_message": "Authentication backend temporarily unavailable",
            },
        )

    # -------------------------------------------------------------------------
    # Default allow
    # -------------------------------------------------------------------------
    return payload


def verify_google_token(authorization: str = Header(None)) -> dict:
    """
    Verifies Google ID token.
    Access is ALLOWED by default.
    Only explicitly blocked users are denied.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise _unauthorized("AUTH_MISSING_AUTH_HEADER", "Missing Authorization header")

    token = authorization.replace("Bearer ", "").strip()
    return verify_google_id_token(token)
