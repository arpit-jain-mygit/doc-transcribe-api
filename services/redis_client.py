import os
import redis
import logging
import time

# ---------------------------------------------------------
# LOGGING
# ---------------------------------------------------------
logger = logging.getLogger("api.redis")

# ---------------------------------------------------------
# REDIS INIT
# ---------------------------------------------------------
REDIS_URL = os.environ.get("REDIS_URL")
if not REDIS_URL:
    raise RuntimeError("REDIS_URL not set")

logger.info(f"[REDIS] Initializing Redis client REDIS_URL={REDIS_URL}")

redis_client = redis.from_url(
    REDIS_URL,
    decode_responses=True,
)

# ---------------------------------------------------------
# CONNECTION DIAGNOSTICS
# ---------------------------------------------------------
try:
    t0 = time.time()
    pong = redis_client.ping()
    ms = int((time.time() - t0) * 1000)

    logger.info(f"[REDIS] Connected OK ping={pong} latency={ms}ms")

    try:
        cid = redis_client.client_id()
        logger.info(f"[REDIS] client_id={cid}")
    except Exception:
        logger.info("[REDIS] client_id not available")

except Exception as e:
    logger.error(f"[REDIS] Initial ping failed: {e}")
