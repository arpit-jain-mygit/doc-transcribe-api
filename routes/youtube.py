from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from auth import verify_user
from jobs import create_job

router = APIRouter()

class YoutubeJob(BaseModel):
    type: str  # TRANSCRIPTION
    url: str

@router.post("/youtube")
def submit_youtube_job(
    payload: YoutubeJob,
    user=Depends(verify_user)
):
    job = create_job(
        user_id=user.email,
        job_type=payload.type,
        source="youtube",
        input_url=payload.url
    )

    return {"job_id": job.id}
