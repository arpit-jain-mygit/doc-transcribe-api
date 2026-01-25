from fastapi import APIRouter
from services.redis_client import redis_client

router = APIRouter()

@router.get("/jobs/{job_id}")
def get_job_status(job_id: str):
    key = f"job_status:{job_id}"

    job = redis_client.hgetall(key)

    # Job not found (never error)
    if not job:
        return {
            "job_id": job_id,
            "status": "NOT_FOUND",
        }

    # Redis returns bytes → decode safely
    decoded = {}
    for k, v in job.items():
        try:
            decoded[k.decode()] = v.decode()
        except Exception:
            decoded[str(k)] = str(v)

    return {
        "job_id": decoded.get("job_id", job_id),
        "status": decoded.get("status", "UNKNOWN"),
        "job_type": decoded.get("job_type"),
        "input_type": decoded.get("input_type"),
        "attempts": int(decoded.get("attempts", 0)),
        "output_path": decoded.get("output_path"),
        "error": decoded.get("error"),
        "updated_at": decoded.get("updated_at"),
    }
