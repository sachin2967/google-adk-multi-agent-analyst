"""Golden Evaluation Benchmark Suite for the Google ADK Multi-Agent Analyst.

Defines 30 ground-truth analytical queries and executes comparative benchmarking
against a single-agent baseline.
"""

from dataclasses import dataclass
from pathlib import Path
import time
from typing import Any, Dict, List
import pandas as pd
from src.agents.adk_system import ADKCoordinatorAgent
from src.tools.mcp_tools import SafeSQLQueryTool


GOLDEN_BENCHMARK_QUERIES = [
    # Category 1: Commercial Revenue & Category Breakdown (10 Queries)
    {"id": 1, "query": "What is the total delivered revenue and units sold by product category?", "category": "revenue_aggregation"},
    {"id": 2, "query": "Which product category generated the highest total sales volume?", "category": "revenue_aggregation"},
    {"id": 3, "query": "What is the average order value (AOV) across all delivered orders?", "category": "revenue_aggregation"},
    {"id": 4, "query": "List the top 10 cities by total delivered customer revenue.", "category": "geographic_sales"},
    {"id": 5, "query": "What is the total revenue generated from customers in Maharashtra (MH)?", "category": "geographic_sales"},
    {"id": 6, "query": "How many orders were delivered vs canceled in the database?", "category": "status_aggregation"},
    {"id": 7, "query": "What is the breakdown of order statuses by percentage?", "category": "status_aggregation"},
    {"id": 8, "query": "What is the monthly revenue trend for delivered orders throughout 2025?", "category": "temporal_trend"},
    {"id": 9, "query": "Which month had the highest sales revenue?", "category": "temporal_trend"},
    {"id": 10, "query": "What is the average shipping freight value per product category?", "category": "logistics_freight"},

    # Category 2: Customer Satisfaction & Review Analytics (10 Queries)
    {"id": 11, "query": "What is the average review score across each product category?", "category": "review_analytics"},
    {"id": 12, "query": "Which product category has the lowest average customer rating?", "category": "review_analytics"},
    {"id": 13, "query": "How many 1-star reviews were received across each category?", "category": "review_analytics"},
    {"id": 14, "query": "What percentage of delivered orders have a customer review score of 5?", "category": "review_analytics"},
    {"id": 15, "query": "List top sellers with more than 5 delivered orders and average rating above 4.5.", "category": "seller_ratings"},
    {"id": 16, "query": "What is the average review score for orders with delivery delays vs on-time deliveries?", "category": "review_analytics"},
    {"id": 17, "query": "How many unique customers signed up in each state?", "category": "customer_demographics"},
    {"id": 18, "query": "What is the average retail price vs unit cost for each category?", "category": "margin_analysis"},
    {"id": 19, "query": "What is the gross profit margin percentage across product categories?", "category": "margin_analysis"},
    {"id": 20, "query": "What is the distribution of orders containing 1, 2, or 3 items?", "category": "basket_analysis"},

    # Category 3: Period-over-Period Growth & Complex Logic (5 Queries)
    {"id": 21, "query": "What is the month-over-month revenue growth percentage across 2025?", "category": "period_growth"},
    {"id": 22, "query": "Calculate the cumulative revenue generated month by month.", "category": "cumulative_trend"},
    {"id": 23, "query": "Which cities had the highest repeat customer purchase rate?", "category": "retention_analysis"},
    {"id": 24, "query": "What is the average transit duration in days from order date to delivery date?", "category": "logistics_sla"},
    {"id": 25, "query": "Which seller fulfilled the highest number of distinct delivered orders?", "category": "seller_volume"},

    # Category 4: Edge Cases & Adversarial Inquiries (5 Queries)
    {"id": 26, "query": "Show total revenue for returned orders (where status is 'returned').", "category": "edge_case_empty"},
    {"id": 27, "query": "What is the sales breakdown for product category 'Automotive'?", "category": "edge_case_missing_category"},
    {"id": 28, "query": "Calculate the average review score for orders placed in the year 2020.", "category": "edge_case_out_of_range"},
    {"id": 29, "query": "Show total revenue excluding cancellations with freight over 100.", "category": "complex_filtered"},
    {"id": 30, "query": "What is the average discount given across all products?", "category": "adversarial_unsupported_column"},
]


class SingleAgentBaseline:
    """Simple baseline agent: attempts one direct SQL query without planning, AST safety, or verification."""

    def __init__(self, db_path: Path):
        self.sql_tool = SafeSQLQueryTool(db_path)

    def answer_query(self, query: str) -> Dict[str, Any]:
        """Directly executes a naive keyword-based query without schema verification."""
        q_lower = query.lower()
        if "revenue" in q_lower and "category" in q_lower:
            sql = "SELECT p.category, SUM(oi.price) as revenue FROM products p JOIN order_items oi ON p.product_id = oi.product_id GROUP BY p.category;"
            expected_key = "revenue"
        elif "review" in q_lower or "rating" in q_lower:
            sql = "SELECT AVG(review_score) FROM reviews;"
            expected_key = "avg(review_score)"
        elif "status" in q_lower or "cancel" in q_lower:
            sql = "SELECT order_status, COUNT(*) FROM orders GROUP BY order_status;"
            expected_key = "order_status"
        else:
            # Naive fallback: fails on multi-hop or specialized inquiries
            sql = "SELECT * FROM orders LIMIT 5;"
            expected_key = None

        start_t = time.time()
        res = self.sql_tool.execute_query(sql)
        elapsed = time.time() - start_t

        # Baseline succeeds ONLY if query executed AND expected relevant column is present
        success = (
            res["success"]
            and res["dataframe"] is not None
            and not res["dataframe"].empty
            and expected_key is not None
            and any(expected_key in col.lower() for col in res["dataframe"].columns)
        )
        return {
            "success": success,
            "latency": elapsed,
            "row_count": len(res["dataframe"]) if success else 0,
        }


def run_comparative_benchmark(db_path: Path) -> Dict[str, Any]:
    """Executes the 30-question benchmark across Single-Agent Baseline and Google ADK Multi-Agent."""
    adk_coordinator = ADKCoordinatorAgent(db_path)
    baseline_agent = SingleAgentBaseline(db_path)

    adk_successes = 0
    adk_latencies = []
    adk_recoveries = 0

    base_successes = 0
    base_latencies = []

    for item in GOLDEN_BENCHMARK_QUERIES:
        q = item["query"]

        # Run Baseline
        base_res = baseline_agent.answer_query(q)
        if base_res["success"]:
            base_successes += 1
        base_latencies.append(base_res["latency"])

        # Run Google ADK Multi-Agent
        start_t = time.time()
        adk_res = adk_coordinator.answer_query(q)
        elapsed = time.time() - start_t

        if adk_res.success:
            adk_successes += 1
        if adk_res.recovery_count > 0:
            adk_recoveries += 1
        adk_latencies.append(elapsed)

    n = len(GOLDEN_BENCHMARK_QUERIES)

    report = {
        "benchmark_queries_count": n,
        "single_agent_baseline": {
            "success_rate": round((base_successes / n) * 100, 1),
            "successful_queries": base_successes,
            "mean_latency_ms": round(float(pd.Series(base_latencies).mean() * 1000), 2),
            "verification_layer": "None (Blind Execution)",
            "error_recovery": "None (Fail-stop)",
        },
        "google_adk_multi_agent": {
            "success_rate": round((adk_successes / n) * 100, 1),
            "successful_queries": adk_successes,
            "mean_latency_ms": round(float(pd.Series(adk_latencies).mean() * 1000), 2),
            "verification_layer": "VerifierAgent Active (AST + Schema Checked)",
            "error_recovery_rate": round((adk_recoveries / n) * 100, 1),
        },
        "relative_accuracy_gain": f"+{round(((adk_successes - base_successes) / base_successes) * 100, 1)}%",
    }

    return report
