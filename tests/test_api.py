"""Integration tests for Google ADK FastAPI service using TestClient."""

from fastapi.testclient import TestClient
from api.app import app

client = TestClient(app)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database_connected"] is True
    assert "Google ADK" in data["framework"]


def test_schema_endpoint():
    response = client.get("/api/schema")
    assert response.status_code == 200
    schema = response.json()
    assert "customers" in schema
    assert "orders" in schema
    assert "products" in schema


def test_benchmark_report_endpoint():
    response = client.get("/api/benchmark")
    assert response.status_code == 200
    data = response.json()
    assert "google_adk_multi_agent" in data
    assert data["google_adk_multi_agent"]["success_rate"] == 100.0
    assert data["single_agent_baseline"]["success_rate"] == 40.0


def test_analyze_valid_query():
    payload = {
        "query": "What is the total revenue by product category?",
        "max_retries": 1,
    }
    response = client.post("/api/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert len(data["agent_execution_trace"]) > 0
    assert len(data["data_records"]) > 0


def test_analyze_invalid_payload():
    response = client.post("/api/analyze", json={})
    assert response.status_code == 422
