from datetime import datetime, timezone

from fastapi import HTTPException

from app.config import settings
from app.redis_client import redis_client


INPUT_PRICE_PER_1K = 0.00015
OUTPUT_PRICE_PER_1K = 0.0006


def _usage_key(user_id: str) -> str:
    month = datetime.now(timezone.utc).strftime("%Y-%m")
    return f"usage:{month}:{user_id}"


def _estimate_cost(input_tokens: int, output_tokens: int) -> float:
    return round(
        (input_tokens / 1000 * INPUT_PRICE_PER_1K) +
        (output_tokens / 1000 * OUTPUT_PRICE_PER_1K),
        6,
    )


def check_budget(user_id: str) -> dict:
    key = _usage_key(user_id)
    current_cost = float(redis_client.hget(key, "cost_usd") or 0.0)
    if current_cost >= settings.monthly_budget_usd:
        raise HTTPException(
            status_code=402,
            detail={
                "error": "Monthly budget exceeded",
                "used_usd": round(current_cost, 6),
                "budget_usd": settings.monthly_budget_usd,
            },
        )
    return {"used_usd": round(current_cost, 6), "budget_usd": settings.monthly_budget_usd}


def record_usage(user_id: str, input_tokens: int, output_tokens: int) -> dict:
    key = _usage_key(user_id)
    cost = _estimate_cost(input_tokens, output_tokens)

    pipeline = redis_client.pipeline()
    pipeline.hincrby(key, "input_tokens", input_tokens)
    pipeline.hincrby(key, "output_tokens", output_tokens)
    pipeline.hincrby(key, "request_count", 1)
    pipeline.hincrbyfloat(key, "cost_usd", cost)
    pipeline.expire(key, 60 * 60 * 24 * 32)
    input_total, output_total, request_total, cost_total, _ = pipeline.execute()

    return {
        "input_tokens": int(input_total),
        "output_tokens": int(output_total),
        "request_count": int(request_total),
        "cost_usd": round(float(cost_total), 6),
    }
