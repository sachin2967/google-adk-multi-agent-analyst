"""Offline end-to-end exercise of ADK -> MCP -> SQLite -> ADK orchestration."""

import asyncio

from google.adk.apps import App
from google.adk.models.base_llm import BaseLlm
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.adk.runners import InMemoryRunner
from google.genai import types
from pydantic import PrivateAttr

from src.agents.adk_system import build_analyst_agent
from src.agents.service import _run_agent


class ScriptedModel(BaseLlm):
    """Deterministic test double; validates orchestration, not language quality."""

    model: str = "scripted-test-model"
    _calls: int = PrivateAttr(default=0)

    async def generate_content_async(
        self, llm_request: LlmRequest, stream: bool = False
    ):
        del stream
        self._calls += 1
        if self._calls == 1:
            text = (
                '{"supported":true,"metric":"revenue","group_by":"category",'
                '"order_status":null,"state":null,"reason":"Supported aggregate."}'
            )
            part = types.Part.from_text(text=text)
        elif self._calls == 2:
            tool_names = [
                declaration.name
                for tool in (llm_request.config.tools or [])
                for declaration in (tool.function_declarations or [])
            ]
            tool_name = next(
                name for name in tool_names if name.endswith("analyze_commerce")
            )
            part = types.Part.from_function_call(
                name=tool_name,
                args={"metric": "revenue", "group_by": "category", "limit": 5},
            )
        elif self._calls == 3:
            part = types.Part.from_text(
                text="MCP aggregate call completed successfully."
            )
        else:
            part = types.Part.from_text(
                text="Verified: delivered revenue is grouped by product category from the MCP result."
            )
        yield LlmResponse(content=types.Content(role="model", parts=[part]))


def test_sequential_adk_workflow_calls_real_mcp_server_offline():
    async def exercise():
        app = App(
            name="test_commerce_analytics",
            root_agent=build_analyst_agent(model=ScriptedModel()),
        )
        async with InMemoryRunner(app=app) as runner:
            session = await runner.session_service.create_session(
                app_name=app.name, user_id="test-user", session_id="test-session"
            )
            events = [
                event
                async for event in runner.run_async(
                    user_id="test-user",
                    session_id=session.id,
                    new_message=types.Content(
                        role="user",
                        parts=[
                            types.Part.from_text(text="Revenue by product category")
                        ],
                    ),
                )
            ]
        authors = {event.author for event in events}
        assert {
            "analytics_planner",
            "mcp_analytics_executor",
            "analytics_verifier",
        } <= authors
        assert any(
            part.function_call
            for event in events
            if event.content
            for part in (event.content.parts or [])
        )
        final_text = " ".join(
            part.text
            for event in events
            if event.author == "analytics_verifier" and event.content
            for part in (event.content.parts or [])
            if part.text
        )
        assert "Verified" in final_text

    asyncio.run(exercise())


def test_service_collects_final_answer_and_actual_tool_arguments_offline():
    async def exercise():
        app = App(
            name="commerce_analytics",
            root_agent=build_analyst_agent(model=ScriptedModel()),
        )
        result = await _run_agent(
            "Revenue by product category", app=app, capture_trace=True
        )
        assert "Verified" in result["answer"]
        calls = [
            c for c in result["tool_calls"] if c["name"].endswith("analyze_commerce")
        ]
        assert calls[0]["args"]["metric"] == "revenue"
        assert calls[0]["args"]["group_by"] == "category"
        assert result["event_count"] > 0

    asyncio.run(exercise())
