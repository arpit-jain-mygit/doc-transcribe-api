import json
from services.redis_client import redis_client

QUEUE_NAME = "doc_jobs"


def enqueue_job(job: dict):
    """
    Push job payload to Redis queue
    """
    redis_client.lpush(QUEUE_NAME, json.dumps(job))
