"""Read-only, parameterized analytics tools exposed through MCP."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Literal
from urllib.parse import quote

from mcp.server.fastmcp import FastMCP

DEFAULT_DB = Path(__file__).resolve().parents[2] / "data" / "ecommerce.db"
mcp = FastMCP(
    "commerce-analytics",
    instructions="Read-only analytics over the bundled demo commerce database.",
)

METRICS = {"revenue", "orders", "average_review", "average_delivery_days"}
DIMENSIONS = {"none", "category", "state", "month", "status"}


def _connect(db_path: Path = DEFAULT_DB) -> sqlite3.Connection:
    """Open a SQLite database read-only and enforce query-only mode."""
    uri = f"file:{quote(db_path.resolve().as_posix(), safe='/:')}?mode=ro"
    connection = sqlite3.connect(uri, uri=True, timeout=3)
    connection.execute("PRAGMA query_only = ON")
    connection.execute("PRAGMA busy_timeout = 3000")
    return connection


def inspect_schema(db_path: Path = DEFAULT_DB) -> dict[str, Any]:
    """Return table/column names only; sample customer records are not exposed."""
    result: dict[str, Any] = {}
    with _connect(db_path) as connection:
        tables = connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ).fetchall()
        for (table,) in tables:
            # Table names originate from sqlite_master and are quoted defensively.
            escaped = table.replace('"', '""')
            columns = connection.execute(f'PRAGMA table_info("{escaped}")').fetchall()
            result[table] = [{"name": row[1], "type": row[2]} for row in columns]
    return result


def query_metrics(
    metric: str,
    group_by: str = "none",
    order_status: str | None = None,
    state: str | None = None,
    limit: int = 20,
    db_path: Path = DEFAULT_DB,
) -> dict[str, Any]:
    """Compute supported commerce aggregates; SQL structure is fixed and filters are bound."""
    if metric not in METRICS:
        raise ValueError(f"Unsupported metric. Choose one of: {sorted(METRICS)}")
    if group_by not in DIMENSIONS:
        raise ValueError(f"Unsupported grouping. Choose one of: {sorted(DIMENSIONS)}")
    if not 1 <= limit <= 100:
        raise ValueError("limit must be between 1 and 100")
    if order_status is not None and order_status not in {
        "delivered",
        "canceled",
        "returned",
        "shipped",
        "processing",
    }:
        raise ValueError("Unsupported order status")
    if state is not None and (
        len(state) != 2 or not state.isalpha() or not state.isupper()
    ):
        raise ValueError("state must be a two-letter uppercase code")

    value_expr = {
        "revenue": "SUM(oi.price * oi.quantity)",
        "orders": "COUNT(DISTINCT o.order_id)",
        "average_review": "AVG(r.review_score)",
        "average_delivery_days": "AVG(julianday(o.delivered_date) - julianday(o.order_date))",
    }[metric]
    joins: list[str] = []
    if metric == "revenue":
        joins.append("JOIN order_items oi ON oi.order_id = o.order_id")
    elif metric == "average_review":
        joins.append("JOIN reviews r ON r.order_id = o.order_id")
    default_filter = (
        "o.delivered_date IS NOT NULL" if metric == "average_delivery_days" else "1 = 1"
    )
    if metric == "revenue" and order_status is None and group_by != "status":
        default_filter = "o.order_status = 'delivered'"

    group_expr = {
        "none": None,
        "category": "p.category",
        "state": "c.customer_state",
        "month": "strftime('%Y-%m', o.order_date)",
        "status": "o.order_status",
    }[group_by]
    if group_by == "category":
        if metric in {"average_review", "average_delivery_days"}:
            # Attach one order to each category, avoiding duplicate weighting when
            # the same order has several items in a category.
            joins = [
                "JOIN (SELECT DISTINCT oi3.order_id, p.category FROM order_items oi3 JOIN products p ON p.product_id = oi3.product_id) oc ON oc.order_id = o.order_id"
            ]
            if metric == "average_review":
                joins.append("JOIN reviews r ON r.order_id = o.order_id")
            group_expr = "oc.category"
        else:
            if metric != "revenue":
                joins.append("JOIN order_items oi ON oi.order_id = o.order_id")
            joins.append("JOIN products p ON p.product_id = oi.product_id")
    if group_by == "state" or state:
        joins.append("JOIN customers c ON c.customer_id = o.customer_id")
    joins = list(dict.fromkeys(joins))
    select = f"{group_expr} AS group_value, " if group_expr else ""
    group_clause = f" GROUP BY {group_expr}" if group_expr else ""
    filters = [default_filter]
    params: list[Any] = []
    if order_status:
        filters.append("o.order_status = ?")
        params.append(order_status)
    if state:
        filters.append("c.customer_state = ?")
        params.append(state)
    sql = (
        f"SELECT {select}{value_expr} AS value FROM orders o {' '.join(joins)} "
        f"WHERE {' AND '.join(filters)}{group_clause} ORDER BY value DESC LIMIT ?"
    )
    params.append(limit)
    with _connect(db_path) as connection:
        rows = connection.execute(sql, params).fetchall()
        columns = [
            description[0]
            for description in connection.execute(sql, params).description
        ]
    records = [dict(zip(columns, row)) for row in rows]
    return {
        "metric": metric,
        "group_by": group_by,
        "row_count": len(records),
        "records": records,
    }


@mcp.tool()
def get_analytics_schema() -> dict[str, Any]:
    """List available commerce tables and columns without exposing sample rows."""
    return inspect_schema()


@mcp.tool()
def analyze_commerce(
    metric: Literal["revenue", "orders", "average_review", "average_delivery_days"],
    group_by: Literal["none", "category", "state", "month", "status"] = "none",
    order_status: Literal["delivered", "canceled", "returned", "shipped", "processing"]
    | None = None,
    state: str | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    """Return a supported, read-only commerce aggregate. Never accepts SQL or Python code."""
    return query_metrics(metric, group_by, order_status, state, limit)


def main() -> None:
    """Run the MCP server over stdio for a local ADK client."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
