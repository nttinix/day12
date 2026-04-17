import json
import uuid

from app.config import settings
from app.redis_client import redis_client


def get_or_create_session_id(session_id: str | None) -> str:
    return session_id or uuid.uuid4().hex


def _history_key(user_id: str, session_id: str) -> str:
    return f"history:{user_id}:{session_id}"


def get_history(user_id: str, session_id: str) -> list[dict]:
    key = _history_key(user_id, session_id)
    messages = redis_client.lrange(key, 0, -1)
    return [json.loads(message) for message in messages]


def append_message(user_id: str, session_id: str, role: str, content: str) -> list[dict]:
    key = _history_key(user_id, session_id)
    entry = json.dumps({"role": role, "content": content}, ensure_ascii=True)

    pipeline = redis_client.pipeline()
    pipeline.rpush(key, entry)
    pipeline.ltrim(key, -settings.max_history_messages, -1)
    pipeline.expire(key, settings.history_ttl_seconds)
    pipeline.execute()

    return get_history(user_id, session_id)
