# worker/utils/cancellation.py

import redis
import os

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
CANCEL_KEY_PREFIX = "task_cancel:"
CANCEL_TTL_SECONDS = 3600  # auto-expire flags after 1 hour

_redis_client = None

def _get_redis():
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(REDIS_URL, decode_responses=True)
    return _redis_client


def request_cancellation(task_id: str):
    """Set the cancellation flag for a task in Redis."""
    _get_redis().setex(f"{CANCEL_KEY_PREFIX}{task_id}", CANCEL_TTL_SECONDS, "1")


def is_cancelled(task_id: str) -> bool:
    """Check if a cancellation has been requested for this task."""
    return _get_redis().exists(f"{CANCEL_KEY_PREFIX}{task_id}") == 1


def clear_cancellation(task_id: str):
    """Clean up the cancellation flag after task ends."""
    _get_redis().delete(f"{CANCEL_KEY_PREFIX}{task_id}")