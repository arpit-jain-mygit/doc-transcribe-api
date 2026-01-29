from pydantic import BaseModel
from typing import Literal

class JobRequest(BaseModel):
    job_type: Literal["TRANSCRIBE", "OCR"]
    input_type: Literal["FILE"]
    gcs_uri: str
    filename: str
