from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes.upload import router as upload_router
from routes.status import router as status_router
from routes.health import router as health_router

app = FastAPI(title="Doc Transcribe API")

# ✅ CORS FIX
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/cors-test")
def cors_test():
    return {"ok": True}

app.include_router(health_router)
app.include_router(upload_router)
app.include_router(status_router)
