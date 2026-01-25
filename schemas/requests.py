from pydantic import BaseModel, HttpUrl

class OCRJobRequest(BaseModel):
    local_path: str


class TranscriptionJobRequest(BaseModel):
    url: HttpUrl
