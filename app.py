from fastapi import FastAPI

from routes import jobs, status, dlq, health

app = FastAPI(
    title="Doc-Transcribe API",
    version="1.0.0"
)

app.include_router(jobs.router)
app.include_router(status.router)
app.include_router(dlq.router)
app.include_router(health.router)
