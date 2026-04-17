import signal
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.auth import verify_api_key
from app.chat_store import append_message, get_history, get_or_create_session_id
from app.config import settings
from app.cost_guard import check_budget, record_usage
from app.llm import ask_llm, count_tokens_estimate
from app.logging_utils import configure_logging, log_event
from app.rate_limiter import check_rate_limit
from app.redis_client import redis_client


logger = configure_logging(settings.log_level)
start_time = time.time()
instance_id = uuid.uuid4().hex[:8]
is_ready = False


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    user_id: str = Field(..., min_length=1, max_length=100)
    session_id: str | None = Field(default=None, max_length=100)


class AskResponse(BaseModel):
    session_id: str
    user_id: str
    answer: str
    history_length: int
    model: str
    served_by: str
    timestamp: str


@asynccontextmanager
async def lifespan(_: FastAPI):
    global is_ready
    log_event(logger, "startup", app=settings.app_name, environment=settings.environment)
    try:
        redis_client.ping()
        is_ready = True
        log_event(logger, "redis_ready", redis_url=settings.redis_url)
    except Exception as exc:
        is_ready = False
        log_event(logger, "startup_error", error=str(exc))
    yield
    is_ready = False
    log_event(logger, "shutdown")


app = FastAPI(title=settings.app_name, version=settings.app_version, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins or ["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-API-Key"],
)


@app.middleware("http")
async def request_logging(request: Request, call_next):
    started = time.time()
    try:
        response: Response = await call_next(request)
    except Exception as exc:
        log_event(
            logger,
            "request_error",
            path=request.url.path,
            method=request.method,
            error=str(exc),
        )
        raise

    duration_ms = round((time.time() - started) * 1000, 1)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    log_event(
        logger,
        "request",
        path=request.url.path,
        method=request.method,
        status=response.status_code,
        duration_ms=duration_ms,
        instance_id=instance_id,
    )
    return response


@app.get("/health")
def health():
    redis_status = "ok"
    try:
        redis_client.ping()
    except Exception:
        redis_status = "error"

    return {
        "status": "ok" if redis_status == "ok" else "degraded",
        "app": settings.app_name,
        "version": settings.app_version,
        "instance_id": instance_id,
        "uptime_seconds": round(time.time() - start_time, 1),
        "checks": {"redis": redis_status},
    }


@app.get("/ready")
def ready():
    if not is_ready:
        raise HTTPException(status_code=503, detail="Application not ready")
    try:
        redis_client.ping()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Redis unavailable: {exc}") from exc
    return {"ready": True, "instance_id": instance_id}


@app.post("/ask", response_model=AskResponse)
def ask(body: AskRequest, _: str = Depends(verify_api_key)):
    session_id = get_or_create_session_id(body.session_id)
    check_rate_limit(body.user_id)
    check_budget(body.user_id)

    prior_history = get_history(body.user_id, session_id)
    append_message(body.user_id, session_id, "user", body.question)
    answer = ask_llm(body.question, prior_history)
    full_history = append_message(body.user_id, session_id, "assistant", answer)

    input_tokens = count_tokens_estimate([body.question] + [m["content"] for m in prior_history])
    output_tokens = count_tokens_estimate([answer])
    usage = record_usage(body.user_id, input_tokens, output_tokens)

    log_event(
        logger,
        "ask_completed",
        user_id=body.user_id,
        session_id=session_id,
        history_length=len(full_history),
        cost_usd=usage["cost_usd"],
    )

    return AskResponse(
        session_id=session_id,
        user_id=body.user_id,
        answer=answer,
        history_length=len(full_history),
        model=settings.llm_model if settings.llm_provider == "openai" else "mock-llm",
        served_by=instance_id,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@app.get("/history/{user_id}/{session_id}")
def history(user_id: str, session_id: str, _: str = Depends(verify_api_key)):
    messages = get_history(user_id, session_id)
    return {"user_id": user_id, "session_id": session_id, "messages": messages}


def _handle_sigterm(signum, _frame):
    log_event(logger, "signal_received", signum=signum, signal_name="SIGTERM")


signal.signal(signal.SIGTERM, _handle_sigterm)
