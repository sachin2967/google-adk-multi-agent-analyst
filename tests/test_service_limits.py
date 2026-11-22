"""Resource bounds must release capacity on provider errors and cancellation."""

import asyncio

import pytest
from fastapi.testclient import TestClient

import api.app as api
from src.agents import service


def test_timeout_releases_capacity(monkeypatch):
    async def hang(_):
        await asyncio.sleep(30)

    monkeypatch.setattr(service, "_run_agent", hang)
    monkeypatch.setattr(service, "TIMEOUT_SECONDS", 0.01)
    for _ in range(3):
        with pytest.raises(TimeoutError):
            asyncio.run(service.run_analysis("test question"))


def test_capacity_is_bounded_and_cancel_safe(monkeypatch):
    async def exercise():
        started = asyncio.Event()

        async def hang(_):
            started.set()
            await asyncio.sleep(30)

        monkeypatch.setattr(service, "_run_agent", hang)
        tasks = [asyncio.create_task(service.run_analysis("test")) for _ in range(2)]
        await started.wait()
        with pytest.raises(service.AnalysisBusyError):
            await service.run_analysis("overloaded")
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

        async def succeed(_):
            return {"answer": "ok", "event_count": 1}

        monkeypatch.setattr(service, "_run_agent", succeed)
        assert (await service.run_analysis("recovered"))["answer"] == "ok"

    asyncio.run(exercise())


@pytest.mark.parametrize(
    "error,status",
    [
        (TimeoutError(), 504),
        (service.AnalysisBusyError("busy"), 429),
        (service.AnalysisOutputError("empty verifier"), 502),
    ],
)
def test_http_error_mapping(monkeypatch, error, status):
    monkeypatch.setenv("ANALYST_MODEL", "test-provider")

    async def fail(_):
        raise error

    monkeypatch.setattr(api, "run_analysis", fail)
    with TestClient(api.app) as client:
        assert (
            client.post(
                "/api/analyze", json={"query": "revenue by category"}
            ).status_code
            == status
        )


def test_mcp_process_does_not_receive_provider_secrets(monkeypatch):
    import src.agents.adk_system as system

    monkeypatch.setenv("GOOGLE_API_KEY", "must-not-cross-tool-boundary")
    monkeypatch.setenv("PYTHONPATH", "/opt/python/lib/python3.11/site-packages")
    captured = {}
    original = system.StdioServerParameters

    def capture(**kwargs):
        captured.update(kwargs)
        return original(**kwargs)

    monkeypatch.setattr(system, "StdioServerParameters", capture)
    system._mcp_toolset()
    assert "GOOGLE_API_KEY" not in captured["env"]
    assert captured["env"]["PYTHONPATH"].endswith(
        "/opt/python/lib/python3.11/site-packages"
    )
