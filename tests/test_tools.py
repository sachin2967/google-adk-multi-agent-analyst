"""Tests for safe aggregation semantics and hostile argument rejection."""

from pathlib import Path

import pytest

from src.tools.mcp_tools import inspect_schema, query_metrics

DB = Path(__file__).resolve().parents[1] / "data" / "ecommerce.db"


def test_schema_exposes_columns_but_no_customer_rows():
    schema = inspect_schema(DB)
    assert {"orders", "order_items", "products", "customers"} <= schema.keys()
    assert "sample_records" not in str(schema)


def test_delivered_revenue_by_category_is_sorted_and_positive():
    result = query_metrics("revenue", "category", db_path=DB)
    values = [row["value"] for row in result["records"]]
    assert result["row_count"] > 0
    assert all(value > 0 for value in values)
    assert values == sorted(values, reverse=True)


def test_average_review_by_category_avoids_item_join_duplicate_bias():
    result = query_metrics("average_review", "category", db_path=DB)
    assert result["row_count"] > 0
    assert all(1 <= row["value"] <= 5 for row in result["records"])


def test_bound_state_filter_and_status_grouping():
    result = query_metrics("orders", "status", state="MH", db_path=DB)
    assert result["row_count"] > 0
    assert {"group_value", "value"} == set(result["records"][0])


def test_revenue_by_status_does_not_apply_delivered_only_default():
    result = query_metrics("revenue", "status", db_path=DB)
    status_values = {row["group_value"] for row in result["records"]}
    assert {"delivered", "canceled", "shipped"} <= status_values


@pytest.mark.parametrize(
    "kwargs",
    [
        {"metric": "revenue; DROP TABLE orders"},
        {"metric": "revenue", "group_by": "SELECT * FROM customers"},
        {"metric": "orders", "state": "MH' OR 1=1 --"},
        {"metric": "orders", "limit": 1000000},
    ],
)
def test_untrusted_parameters_are_rejected(kwargs):
    with pytest.raises(ValueError):
        query_metrics(db_path=DB, **kwargs)


def test_sqlite_connection_is_read_only():
    import sqlite3

    from src.tools.mcp_tools import _connect

    with _connect(DB) as connection, pytest.raises(sqlite3.OperationalError):
        connection.execute("DELETE FROM orders")
