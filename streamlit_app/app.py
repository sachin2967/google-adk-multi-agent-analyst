"""Small UI client for the separate FastAPI service."""

import os

import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="Commerce Analyst", page_icon="📊", layout="wide")
api_url = os.getenv("ANALYST_API_URL", "http://localhost:8000").rstrip("/")
api_headers = {"X-API-Key": os.getenv("ANALYST_API_KEY", "")}
st.title("Commerce Analytics Agent")
st.caption("Google ADK → MCP stdio server → parameterized read-only SQLite aggregates")


def call_api(method, path, payload=None, timeout=10):
    try:
        with requests.Session() as session:
            # Keep operator credentials off ambient HTTP proxies.
            session.trust_env = False
            response = session.request(
                method,
                api_url + path,
                json=payload,
                timeout=timeout,
                headers=api_headers,
            )
            result = response.json()
        if not response.ok:
            st.error(result.get("detail", "API request failed."))
            return None
        return result
    except (requests.RequestException, ValueError):
        st.error(
            "API unavailable or returned an invalid response. Retry after checking service health."
        )
        return None


health = call_api("GET", "/health", timeout=3)
if health is None:
    st.stop()

col1, col2, col3 = st.columns(3)
col1.metric("API", health["status"])
col2.metric("Database", "ready" if health["database_available"] else "missing")
col3.metric("Model", "configured" if health["model_configured"] else "not configured")

chat_tab, metrics_tab, architecture_tab = st.tabs(
    ["Ask the agent", "Explore supported metrics", "Runtime"]
)

with chat_tab:
    question = st.text_area(
        "Analytics question",
        placeholder="Compare delivered revenue by product category",
    )
    if st.button("Analyze", type="primary", disabled=not question.strip()):
        with st.spinner("Running the ADK agent and MCP tool calls…"):
            result = call_api("POST", "/api/analyze", {"query": question}, timeout=70)
        if result is not None:
            st.write(result["answer"])

with metrics_tab:
    metric = st.selectbox(
        "Metric", ["revenue", "orders", "average_review", "average_delivery_days"]
    )
    group = st.selectbox("Group by", ["none", "category", "state", "month", "status"])
    if st.button("Query data"):
        result = call_api("POST", "/api/metrics", {"metric": metric, "group_by": group})
        if result is not None:
            st.dataframe(pd.DataFrame(result["records"]), use_container_width=True)

with architecture_tab:
    st.json(health)
    st.markdown(
        "The API refuses natural-language analysis when no model is configured. It does not silently switch to a keyword heuristic."
    )
    st.markdown(
        "The MCP server accepts metric/group/filter parameters; it never accepts user SQL or Python source."
    )
