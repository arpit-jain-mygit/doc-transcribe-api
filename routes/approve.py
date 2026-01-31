import os
import redis
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends

from services.auth import verify_google_token

router = APIRouter()

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
r = redis.Redis.from_url(REDIS_URL, decode_responses=True)


@router.post("/approve/{job_id}")
def approve_job(
    job_id: str,
    user=Depends(verify_google_token),
):
    key = f"job_status:{job_id}"
    data = r.hgetall(key)

    if not data:
        raise HTTPException(404, "Job not found")

    # 🔒 simple rule: uploader approves (change later if needed)
    if data.get("user") != user["email"]:
        raise HTTPException(403, "Not allowed")

    r.hset(
        key,
        mapping={
            "approved": "true",
            "approved_at": datetime.utcnow().isoformat(),
        },
    )

    return {"status": "approved"}
