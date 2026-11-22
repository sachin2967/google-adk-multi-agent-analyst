"""Bound the cost/lifetime of one explicitly configured ADK analysis request."""

from __future__ import annotations

import asyncio
import os
import time
from threading import BoundedSemaphore
from uuid import uuid4

MAX_CONCURRENT_RUNS = 2  # Per process; deploy with one worker for this pilot.
MAX_LLM_CALLS = 8
MAX_EVENTS = 128
MAX_ANSWER_CHARS = 16000
TIMEOUT_SECONDS = 60
_slots = BoundedSemaphore(MAX_CONCURRENT_RUNS)


class AnalysisBusyError(RuntimeError):
    pass


class AnalysisOutputError(RuntimeError):
    pass


async def _run_agent(query: str) -> dict:
    from google.adk.agents.run_config import RunConfig
    from google.adk.runners import InMemoryRunner
    from google.genai import types

    from src.agents.adk_system import build_app

    adk_app = build_app()
    answers: list[str] = []
    count = 0
    usage = {"prompt_tokens": 0, "candidate_tokens": 0, "thinking_tokens": 0}
    async with InMemoryRunner(app=adk_app) as runner:
        session = await runner.session_service.create_session(
            app_name=adk_app.name,
            user_id="local_api_user",
            session_id=f"request-{uuid4().hex}",
        )
        async for event in runner.run_async(
            user_id="local_api_user",
            session_id=session.id,
            new_message=types.Content(
                role="user", parts=[types.Part.from_text(text=query)]
            ),
            run_config=RunConfig(max_llm_calls=MAX_LLM_CALLS),
        ):
            count += 1
            if count > MAX_EVENTS:
                raise AnalysisOutputError("Agent event budget exceeded.")
            metadata = getattr(event, "usage_metadata", None)
            for key, attribute in (
                ("prompt_tokens", "prompt_token_count"),
                ("candidate_tokens", "candidates_token_count"),
                ("thinking_tokens", "thoughts_token_count"),
            ):
                usage[key] += int(getattr(metadata, attribute, 0) or 0)
            if event.author == "analytics_verifier" and getattr(event, "content", None):
                answers.extend(
                    part.text
                    for part in (event.content.parts or [])
                    if getattr(part, "text", None)
                )
                if sum(map(len, answers)) > MAX_ANSWER_CHARS:
                    raise AnalysisOutputError("Answer size budget exceeded.")
    answer = "\n".join(answers).strip()
    if not answer:
        raise AnalysisOutputError("Verifier did not return a final answer.")
    return {"answer": answer, "event_count": count, "reported_token_usage": usage}


async def run_analysis(query: str) -> dict:
    if not _slots.acquire(blocking=False):
        raise AnalysisBusyError("Analysis capacity is busy; retry later.")
    started = time.perf_counter()
    try:
        async with asyncio.timeout(TIMEOUT_SECONDS):
            result = await _run_agent(query)
        return {
            "query": query,
            **result,
            "model": os.getenv("ANALYST_MODEL", ""),
            "duration_ms": round((time.perf_counter() - started) * 1000, 3),
            "execution_mode": "live_provider",
            "max_llm_calls": MAX_LLM_CALLS,
        }
    finally:
        _slots.release()
