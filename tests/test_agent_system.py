"""Contract tests for genuine ADK composition and explicit model configuration."""

import pytest

from src.agents.adk_system import build_analyst_agent


def test_agent_is_google_adk_agent_with_mcp_toolset():
    from google.adk.agents import LlmAgent, SequentialAgent
    from google.adk.tools.mcp_tool import McpToolset

    agent = build_analyst_agent(model="gemini-2.0-flash")
    assert isinstance(agent, SequentialAgent)
    assert [child.name for child in agent.sub_agents] == [
        "analytics_planner",
        "mcp_analytics_executor",
        "analytics_verifier",
    ]
    executor = agent.sub_agents[1]
    assert isinstance(executor, LlmAgent)
    assert len(executor.tools) == 1
    assert isinstance(executor.tools[0], McpToolset)
    assert executor.tools[0].tool_filter == ["get_analytics_schema", "analyze_commerce"]


def test_agent_requires_explicit_model(monkeypatch):
    monkeypatch.delenv("ANALYST_MODEL", raising=False)
    with pytest.raises(RuntimeError, match="No LLM is configured"):
        build_analyst_agent()


def test_ollama_model_is_configured_as_local_litellm_provider(monkeypatch):
    from google.adk.models.lite_llm import LiteLlm

    monkeypatch.setenv("ANALYST_MODEL", "ollama_chat/qwen3:4b")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://localhost:11434")
    agent = build_analyst_agent()
    model = agent.sub_agents[0].model
    assert isinstance(model, LiteLlm)
    assert model._additional_args["api_base"] == "http://localhost:11434"
    assert "api_key" not in model._additional_args
