from typing import Iterable

from fastapi import HTTPException

from app.config import settings


def _mock_answer(question: str, history: list[dict]) -> str:
    context_hint = ""
    if history:
        last_user_turns = [item["content"] for item in history if item["role"] == "user"][-2:]
        if last_user_turns:
            context_hint = f" Context gan day: {' | '.join(last_user_turns)}."
    return (
        "Mock LLM tra loi: "
        f"Ban hoi '{question}'."
        f"{context_hint} Day la phien ban san sang de thay bang OpenAI khi co API key."
    )


def ask_llm(question: str, history: list[dict]) -> str:
    if settings.llm_provider.lower() != "openai" or not settings.openai_api_key:
        return _mock_answer(question, history)

    try:
        from openai import OpenAI
    except ImportError:
        return _mock_answer(question, history)

    try:
        client = OpenAI(api_key=settings.openai_api_key)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"OpenAI client init failed: {exc}") from exc

    messages: list[dict[str, str]] = [
        {"role": "system", "content": "You are a concise helpful AI chat agent."}
    ]
    messages.extend(history)
    messages.append({"role": "user", "content": question})

    try:
        response = client.chat.completions.create(
            model=settings.llm_model,
            messages=messages,
            temperature=0.2,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"OpenAI request failed: {exc}") from exc

    return response.choices[0].message.content or ""


def count_tokens_estimate(parts: Iterable[str]) -> int:
    text = " ".join(part for part in parts if part)
    return max(1, int(len(text.split()) * 1.3))
