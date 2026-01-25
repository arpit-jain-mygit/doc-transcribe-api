import json
from fastapi import APIRouter
from services.redis_client import redis_client
from config import DLQ_NAME

router = APIRouter(prefix="/dlq", tags=["dlq"])


@router.get("")
def list_dead_letter_jobs(limit: int = 50):
    raw = redis_client.lrange(DLQ_NAME, 0, limit - 1)
    return [json.loads(j) for j in raw]
