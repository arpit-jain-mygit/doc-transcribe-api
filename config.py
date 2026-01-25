import os
from dotenv import load_dotenv

load_dotenv()

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
QUEUE_NAME = os.environ.get("QUEUE_NAME", "doc_jobs")
DLQ_NAME = os.environ.get("DLQ_NAME", "doc_jobs_dead")