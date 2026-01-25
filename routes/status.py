import os
from fastapi import APIRouter, HTTPException
from services.redis_client import redis_client

router = APIRouter(prefix="/jobs", tags=["status"])


@router.get("/{job_id}")
def get_job_status(job_id: str):
    data = redis_client.hgetall(f"job_status:{job_id}")
    if not data:
        raise HTTPException(404, "Job not found")

    return {k: v for k, v in data.items()}


@router.get("/{job_id}/output")
def download_output(job_id: str, upto_page: int | None = None):
    data = redis_client.hgetall(f"job_status:{job_id}")
    path = data.get("output_path")

    if not path or not os.path.exists(path):
        raise HTTPException(404, "Output not available")

    if upto_page is None:
        return open(path, "r", encoding="utf-8").read()

    result = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            result.append(line)
            if line.startswith(f"=== Page {upto_page} ==="):
                break

    return "".join(result)
