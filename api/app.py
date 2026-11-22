"""FastAPI boundary for the ADK and MCP commerce analyst."""

from __future__ import annotations

import os
import sqlite3

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from api.boundary import OperatorBoundary
from src.agents.service import AnalysisBusyError, AnalysisOutputError, run_analysis
from src.tools.mcp_tools import DEFAULT_DB, inspect_schema, query_metrics

app = FastAPI(
    title="ADK MCP Commerce Analyst",
    description="Local-first ADK agent using an isolated read-only MCP analytics server.",
    version="1.0.0",
)
app.add_middleware(OperatorBoundary)


@app.get("/live")
def live():
    return {"status": "alive"}


@app.get("/ready")
def ready():
    if not os.getenv("ANALYST_MODEL", "").strip():
        raise HTTPException(503, "No model configured.")
    try:
        inspect_schema()
    except sqlite3.Error as exc:
        raise HTTPException(503, "Analytics database unavailable.") from exc
    return {"status": "ready", "provider_connectivity": "not_probed"}


class QueryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    query: str = Field(min_length=3, max_length=2000)


class MetricRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    metric: str
    group_by: str = "none"
    order_status: str | None = None
    state: str | None = None
    limit: int = Field(default=20, ge=1, le=100)


@app.get("/health")
def health() -> dict[str, object]:
    configured = bool(os.getenv("ANALYST_MODEL", "").strip())
    return {
        "status": "healthy" if DEFAULT_DB.exists() else "degraded",
        "database_available": DEFAULT_DB.exists(),
        "adk_available": True,
        "mcp_server": "MCP stdio subprocess; read-only allowlisted tools",
        "model_configured": configured,
    }


@app.get("/api/schema")
def get_schema():
    try:
        return inspect_schema()
    except sqlite3.Error as exc:
        raise HTTPException(503, "Analytics database unavailable.") from exc


@app.post("/api/metrics")
def metrics(request: MetricRequest):
    """Deterministic supported aggregation endpoint, useful for tool validation."""
    try:
        return query_metrics(
            request.metric,
            request.group_by,
            request.order_status,
            request.state,
            request.limit,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except sqlite3.Error as exc:
        raise HTTPException(503, "Analytics database unavailable.") from exc


@app.post("/api/analyze")
async def analyze(request: QueryRequest):
    """Run the configured Google ADK agent; no keyword fallback is silently used."""
    if not os.getenv("ANALYST_MODEL", "").strip():
        raise HTTPException(
            status_code=503,
            detail="No model configured. Set ANALYST_MODEL to a local Ollama model or a supported ADK provider.",
        )
    try:
        return await run_analysis(request.query)
    except AnalysisBusyError as exc:
        raise HTTPException(429, str(exc), headers={"Retry-After": "5"}) from exc
    except TimeoutError as exc:
        raise HTTPException(
            504, "Agent request exceeded its execution deadline."
        ) from exc
    except AnalysisOutputError as exc:
        raise HTTPException(502, str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        # Do not expose provider exception strings, credentials, or request internals.
        raise HTTPException(
            status_code=502, detail=f"Agent execution failed ({type(exc).__name__})."
        ) from exc
