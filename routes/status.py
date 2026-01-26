from fastapi import APIRouter, HTTPException
from services.redis_client import redis_client
from services.gcs import generate_signed_url

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

    download_url = generate_signed_url(gcs_uri)

    return {
        "job_id": job_id,
        "download_url": download_url
    }

