"""FastAPI service exposing the Google ADK Multi-Agent Analytical System."""

from pathlib import Path
from typing import Any, Dict, List, Optional
import json
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from src.agents.adk_system import ADKCoordinatorAgent
from src.tools.mcp_tools import SchemaInspectionTool


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "data" / "ecommerce.db"

app = FastAPI(
    title="Google ADK Multi-Agent Analytical API",
    description="Production REST microservice orchestrating hierarchical analytical agents with MCP tools and AST sandboxing.",
    version="1.0.0",
)

coordinator = ADKCoordinatorAgent(DB_PATH)
schema_tool = SchemaInspectionTool(DB_PATH)


class QueryRequest(BaseModel):
    query: str = Field(..., example="What is the total revenue and units sold by product category?")
    max_retries: int = Field(default=2, ge=0, le=5)


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "database_connected": DB_PATH.exists(),
        "framework": "Google ADK (Agent Development Kit 2.0)",
    }


@app.get("/api/schema")
def get_schema():
    """Returns database schema metadata."""
    return schema_tool.get_full_schema()


@app.post("/api/analyze")
def analyze_query(req: QueryRequest):
    """Executes multi-agent analytical workflow and returns structured trace."""
    res = coordinator.answer_query(req.query, max_retries=req.max_retries)

    traces_out = [
        {
            "agent_name": t.agent_name,
            "action": t.action,
            "input_data": str(t.input_data)[:200],
            "output_data": str(t.output_data)[:200],
            "success": t.success,
            "diagnostics": t.diagnostics,
        }
        for t in res.steps_trace
    ]

    return {
        "query": res.query,
        "success": res.success,
        "answer": res.answer,
        "data_records": res.data,
        "recovery_count": res.recovery_count,
        "agent_execution_trace": traces_out,
    }


@app.get("/api/benchmark")
def get_benchmark_report():
    """Fetches frozen 30-question comparative benchmark report."""
    rep_path = PROJECT_ROOT / "benchmark_report.json"
    if not rep_path.exists():
        raise HTTPException(status_code=404, detail="Benchmark report not found. Run scripts/run_benchmark.py first.")

    with open(rep_path) as f:
        return json.load(f)
