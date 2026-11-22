"""HTTP contracts for readiness, bounded metrics, and model configuration."""

from fastapi.testclient import TestClient

from api.app import app

client = TestClient(app)


def test_health_reports_model_configuration_without_claiming_it_is_ready(monkeypatch):
    monkeypatch.delenv("ANALYST_MODEL", raising=False)
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["adk_available"] is True
    assert data["model_configured"] is False
    assert "MCP" in data["mcp_server"]


def test_schema_endpoint_returns_metadata_only():
    response = client.get("/api/schema")
    assert response.status_code == 200
    assert {"orders", "products", "customers"} <= response.json().keys()
    assert "sample_records" not in str(response.json())


def test_metrics_endpoint_returns_grounded_result():
    response = client.post(
        "/api/metrics", json={"metric": "revenue", "group_by": "category"}
    )
    assert response.status_code == 200
    assert response.json()["row_count"] > 0


def test_metrics_reject_unsupported_dimensions():
    response = client.post(
        "/api/metrics", json={"metric": "revenue", "group_by": "sql"}
    )
    assert response.status_code == 422


def test_analyze_requires_model_and_does_not_fallback_to_keywords(monkeypatch):
    monkeypatch.delenv("ANALYST_MODEL", raising=False)
    response = client.post(
        "/api/analyze", json={"query": "How much revenue by category?"}
    )
    assert response.status_code == 503
    assert "No model configured" in response.json()["detail"]


def test_analyze_rejects_oversized_query():
    response = client.post("/api/analyze", json={"query": "x" * 2001})
    assert response.status_code == 422


def test_operator_auth_and_production_key_requirement(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("ANALYST_API_KEY", raising=False)
    assert client.post("/api/analyze", json={"query": "revenue"}).status_code == 503
    assert client.get("/live").status_code == 200
    monkeypatch.setenv("ANALYST_API_KEY", "x" * 32)
    assert client.get("/api/schema").status_code == 401
    assert client.get("/api/schema", headers={"X-API-Key": "x" * 32}).status_code == 200


def test_rejects_whitespace_and_undeclared_request_fields():
    assert client.post("/api/analyze", json={"query": "   "}).status_code == 422
    assert (
        client.post(
            "/api/metrics", json={"metric": "revenue", "sql": "anything"}
        ).status_code
        == 422
    )
