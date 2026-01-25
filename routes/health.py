from fastapi import APIRouter
from services.redis_client import redis_client

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
def health():
    redis_client.ping()
    return {
        "status": "OK",
        "redis": "connected"
    }
