import time
import uuid

from fastapi import HTTPException

from app.config import settings
from app.redis_client import redis_client


WINDOW_SECONDS = 60


def check_rate_limit(user_id: str) -> dict:
    now_ms = int(time.time() * 1000)
    window_start_ms = now_ms - (WINDOW_SECONDS * 1000)
    key = f"rate_limit:{user_id}"

    pipeline = redis_client.pipeline()
    pipeline.zremrangebyscore(key, 0, window_start_ms)
    pipeline.zcard(key)
    _, current_count = pipeline.execute()

    if current_count >= settings.rate_limit_per_minute:
        oldest = redis_client.zrange(key, 0, 0, withscores=True)
        retry_after = WINDOW_SECONDS
        if oldest:
            retry_after = max(1, int((oldest[0][1] + (WINDOW_SECONDS * 1000) - now_ms) / 1000))
        raise HTTPException(
            status_code=429,
            detail={
                "error": "Rate limit exceeded",
                "limit": settings.rate_limit_per_minute,
                "window_seconds": WINDOW_SECONDS,
                "retry_after_seconds": retry_after,
            },
            headers={"Retry-After": str(retry_after)},
        )

    member = f"{now_ms}-{uuid.uuid4().hex}"
    pipeline = redis_client.pipeline()
    pipeline.zadd(key, {member: now_ms})
    pipeline.expire(key, WINDOW_SECONDS + 5)
    pipeline.execute()

    return {
        "limit": settings.rate_limit_per_minute,
        "remaining": settings.rate_limit_per_minute - current_count - 1,
    }
