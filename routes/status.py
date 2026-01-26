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
def download_output(job_id: str):
    data = redis_client.hgetall(f"job_status:{job_id}")

    if not data:
        raise HTTPException(404, "Job not found")

    gcs_uri = data.get("output_path")

    if not gcs_uri or not gcs_uri.startswith("gs://"):
        raise HTTPException(404, "Output not available")

    # For now: return the GCS URI directly
    # (signed URL support can be added later)
    return {
        "job_id": job_id,
        "output_path": gcs_uri
    }

