from fastapi import FastAPI

from routes import jobs, status, dlq, health
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://doc-transcribe-ui.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(jobs.router)
app.include_router(status.router)
app.include_router(dlq.router)
app.include_router(health.router)
