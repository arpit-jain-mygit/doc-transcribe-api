import os
import uuid
import json
from fastapi import APIRouter, UploadFile, File, Form
import redis

from services.gcs import upload_file_to_gcs

router = APIRouter()

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
r = redis.Redis.from_url(REDIS_URL, decode_responses=True)

UPLOAD_TMP = "/tmp/uploads"
os.makedirs(UPLOAD_TMP, exist_ok=True)

@router.post("/upload")
async def upload(
    file: UploadFile = File(...),
    type: str = Form(...)
):
    job_id = uuid.uuid4().hex

    # ----------------------------
    # Save locally (TEMP ONLY)
    # ----------------------------
    local_path = os.path.join(UPLOAD_TMP, f"{job_id}_{file.filename}")
    with open(local_path, "wb") as f:
        f.write(await file.read())

    # ----------------------------
    # Upload to GCS (SOURCE OF TRUTH)
    # ----------------------------
    gcs = upload_file_to_gcs(
        local_path=local_path,
        destination_path=f"jobs/{job_id}/input/{file.filename}",
    )

    # ----------------------------
    # Init job status
    # ----------------------------
    r.hset(
        f"job_status:{job_id}",
        mapping={
            "status": "QUEUED",
            "progress": 0,
            "updated_at": "",
        },
    )

    # ----------------------------
    # Push job to Redis
    # ----------------------------
    job = {
        "job_id": job_id,
        "job_type": type,
        "input_gcs_uri": gcs["gcs_uri"],   # ✅ IMPORTANT
    }

    r.lpush("doc_jobs", json.dumps(job))

    return {"job_id": job_id}
