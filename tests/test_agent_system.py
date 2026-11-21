"""Unit tests for the Google ADK Coordinator, Planner, Executor, and Verifier."""

from pathlib import Path
import pytest
from src.agents.adk_system import ADKCoordinatorAgent


@pytest.fixture
def coordinator():
    db_p = Path(__file__).resolve().parent.parent / "data" / "ecommerce.db"
    return ADKCoordinatorAgent(db_p)


def test_coordinator_category_revenue(coordinator):
    res = coordinator.answer_query("What is the total delivered revenue by product category?")
    assert res.success is True
    assert res.dataframe is not None
    assert not res.dataframe.empty
    assert "total_revenue" in res.dataframe.columns
    assert len(res.steps_trace) >= 3


def test_coordinator_review_analytics(coordinator):
    res = coordinator.answer_query("What is the average review score across each category?")
    assert res.success is True
    assert res.dataframe is not None
    assert "avg_review_score" in res.dataframe.columns


def test_coordinator_verification_trace(coordinator):
    res = coordinator.answer_query("Show me order status percentage breakdown.")
    assert res.success is True
    agent_names = [step.agent_name for step in res.steps_trace]
    assert "CoordinatorAgent" in agent_names
    assert "PlannerAgent" in agent_names
    assert "ToolExecutorAgent" in agent_names
    assert "VerifierAgent" in agent_names
