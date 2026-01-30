from fastapi import APIRouter, HTTPException
import redis

router = APIRouter()

r = redis.Redis(host="REDIS_HOST", port=6379, decode_responses=True)

@router.get("/jobs/{job_id}")
def job_status(job_id: str):
    status_key = f"job_status:{job_id}"
    meta_key = f"job:{job_id}"

    # If worker has started → read live status
    if r.exists(status_key):
        data = r.hgetall(status_key)

        return {
            "job_id": job_id,
            "status": data.get("status", "processing").lower(),
            "progress": int(data.get("progress", 0)),
            "stage": data.get("stage", ""),
            "eta_sec": int(data.get("eta_sec", 0)),
            "current_page": int(data.get("current_page", 0)),
            "total_pages": int(data.get("total_pages", 0)),
            "output_uri": data.get("output_path", ""),
            "error": data.get("error", ""),
        }

    # Worker not started yet → queued
    if r.exists(meta_key):
        meta = r.hgetall(meta_key)

        return {
            "job_id": job_id,
            "status": meta.get("status", "queued"),
            "progress": int(meta.get("progress", 0)),
            "stage": "Waiting in queue",
            "eta_sec": 0,
            "current_page": 0,
            "total_pages": 0,
            "output_uri": meta.get("output_uri", ""),
            "error": meta.get("error", ""),
        }

    raise HTTPException(404, "Job not found")
