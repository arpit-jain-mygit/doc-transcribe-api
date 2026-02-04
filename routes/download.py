from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from google.cloud import storage
from auth import verify_google_token
import io

router = APIRouter()

@router.get("/download/{job_id}")
def download_job_output(
    job_id: str,
    user=Depends(verify_google_token),
):
    from redis_client import r  # use your actual redis import

    job = r.hgetall(f"job_status:{job_id}")
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    output_path = job.get("output_path")
    if not output_path or not output_path.startswith("gs://"):
        raise HTTPException(status_code=404, detail="Output not found")

    # Parse GCS path
    path = output_path.replace("gs://", "")
    bucket_name, blob_path = path.split("/", 1)

    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_path)

    if not blob.exists():
        raise HTTPException(status_code=404, detail="File missing in storage")

    file_stream = io.BytesIO()
    blob.download_to_file(file_stream)
    file_stream.seek(0)

    filename = blob_path.split("/")[-1]

    return StreamingResponse(
        file_stream,
        media_type="text/plain",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        },
    )
