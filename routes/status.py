from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from services.redis_client import redis_client
from services.gcs import generate_signed_url
import requests
import os

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
    if not gcs_uri:
        raise HTTPException(404, "Output not available")

    signed_url = generate_signed_url(gcs_uri)

    r = requests.get(signed_url, stream=True)
    if r.status_code != 200:
        raise HTTPException(500, "Failed to fetch file from storage")

    filename = os.path.basename(gcs_uri)

    return StreamingResponse(
        r.iter_content(chunk_size=8192),
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        },
    )

