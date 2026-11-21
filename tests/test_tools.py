"""Unit tests for MCP tools and Safe SQL execution."""

from pathlib import Path
import pytest
from src.tools.mcp_tools import SafeSQLQueryTool, SchemaInspectionTool, MCPToolRegistry


@pytest.fixture
def db_path():
    p = Path(__file__).resolve().parent.parent / "data" / "ecommerce.db"
    assert p.exists()
    return p


def test_schema_inspection(db_path):
    tool = SchemaInspectionTool(db_path)
    schema = tool.get_full_schema()

    assert "orders" in schema
    assert "order_items" in schema
    assert "products" in schema
    assert "customers" in schema
    assert "reviews" in schema


def test_safe_sql_query(db_path):
    tool = SafeSQLQueryTool(db_path)
    res = tool.execute_query("SELECT COUNT(*) as cnt FROM orders;")

    assert res["success"] is True
    assert res["row_count"] == 1
    assert res["dataframe"].iloc[0]["cnt"] > 0


def test_block_mutating_sql(db_path):
    tool = SafeSQLQueryTool(db_path)
    res = tool.execute_query("DROP TABLE orders;")

    assert res["success"] is False
    assert "Mutating SQL queries" in res["error"]
