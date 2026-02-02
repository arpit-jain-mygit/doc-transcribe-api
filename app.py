# app.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes.upload import router as upload_router
from routes.status import router as status_router
from routes.health import router as health_router
from routes.auth import router as auth_router
from routes.jobs import router as jobs_router


app = FastAPI(title="Doc Transcribe API")

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



app.include_router(auth_router)
app.include_router(health_router)
app.include_router(upload_router)
app.include_router(status_router)
app.include_router(jobs_router)
