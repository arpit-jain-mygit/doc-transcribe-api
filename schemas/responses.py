from pydantic import BaseModel
from typing import Optional

class JobCreatedResponse(BaseModel):
    job_id: str
    status: str = "QUEUED"


class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    job_type: Optional[str]
    input_type: Optional[str]
    attempts: Optional[int]
    output_path: Optional[str]
    error: Optional[str]
    updated_at: Optional[str]
