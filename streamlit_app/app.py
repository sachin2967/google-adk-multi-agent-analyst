"""Interactive Streamlit application demonstrating Google ADK Multi-Agent Analytics."""

from pathlib import Path
import json
import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Google ADK Multi-Agent Data Analyst",
    page_icon="🤖",
    layout="wide",
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "data" / "ecommerce.db"

# Lazy-load agent system
@st.cache_resource
def load_coordinator():
    from src.agents.adk_system import ADKCoordinatorAgent
    return ADKCoordinatorAgent(DB_PATH)


coordinator = load_coordinator()

# --- HEADER ---
st.title("🤖 Google ADK Multi-Agent Analytical System")
st.markdown(
    "**Architecture:** Hierarchical Agent runtime built with Google Agent Development Kit (ADK) concepts, "
    "Model Context Protocol (MCP) tool interfaces, AST execution sandboxing, and automated verification loops."
)

st.divider()

tab1, tab2, tab3 = st.tabs(["💬 Interactive Analytical Chat", "🔬 Live Agent Execution Trace", "📈 30-Question Benchmark"])

with tab1:
    st.subheader("Ask Complex Analytical Questions")

    presets = [
        "What is the total delivered revenue and units sold by product category?",
        "What is the monthly revenue trend for delivered orders throughout 2025?",
        "List the top 10 cities by total delivered customer revenue.",
        "What is the average review score across each product category?",
        "What is the breakdown of order statuses by percentage?",
    ]

    selected_preset = st.selectbox("Or choose a pre-configured analytical query:", options=["Custom Query..."] + presets)

    if selected_preset == "Custom Query...":
        user_query = st.text_input("Enter your analytical question:", value="What is the total revenue and units sold by product category?")
    else:
        user_query = st.text_input("Enter your analytical question:", value=selected_preset)

    if st.button("🚀 Analyze with Google ADK Agents", type="primary"):
        with st.spinner("Coordinator dispatches query to Planner, Executor, and Verifier agents..."):
            res = coordinator.answer_query(user_query)

        st.session_state["latest_res"] = res

        if res.success:
            st.success(f"✅ **Answer:** {res.answer}")
            if res.dataframe is not None and not res.dataframe.empty:
                st.markdown("### 📊 Extracted Data Table")
                st.dataframe(res.dataframe, use_container_width=True)

                # Render automatic chart if numeric columns exist
                num_cols = res.dataframe.select_dtypes(include=["number"]).columns.tolist()
                cat_cols = res.dataframe.select_dtypes(include=["object"]).columns.tolist()

                if cat_cols and num_cols:
                    st.markdown("### 📈 Visual Representation")
                    fig, ax = plt.subplots(figsize=(9, 4))
                    x_col = cat_cols[0]
                    y_col = num_cols[0]
                    ax.bar(res.dataframe[x_col].astype(str), res.dataframe[y_col], color="#4285F4", alpha=0.85)
                    ax.set_ylabel(y_col.replace("_", " ").title())
                    ax.set_title(f"{y_col.replace('_', ' ').title()} by {x_col.replace('_', ' ').title()}")
                    plt.xticks(rotation=35, ha="right")
                    st.pyplot(fig)
        else:
            st.error(f"❌ Analysis failed verification: {res.answer}")

with tab2:
    st.subheader("Audited Agent Step Traces")
    if "latest_res" in st.session_state:
        res = st.session_state["latest_res"]
        st.write(f"**Query:** `{res.query}` | **Automated Recoveries:** `{res.recovery_count}`")

        for idx, step in enumerate(res.steps_trace):
            status_icon = "🟢" if step.success else "🔴"
            with st.expander(f"{status_icon} Step {idx+1}: **{step.agent_name}** → Action: `{step.action}`", expanded=True):
                st.write("**Input:**", step.input_data)
                st.write("**Output:**", step.output_data)
                if step.diagnostics:
                    st.warning(f"Diagnostics: {step.diagnostics}")
    else:
        st.info("Run an analytical query in the first tab to inspect the live execution trace.")

with tab3:
    st.subheader("Rigorous 30-Question Comparative Evaluation")
    rep_file = PROJECT_ROOT / "benchmark_report.json"
    if rep_file.exists():
        with open(rep_file) as f:
            b_data = json.load(f)

        s_base = b_data["single_agent_baseline"]
        s_adk = b_data["google_adk_multi_agent"]

        col1, col2, col3 = st.columns(3)
        col1.metric("Single-Agent Success", f"{s_base['success_rate']}%", f"{s_base['successful_queries']}/30 queries")
        col2.metric("Google ADK Success", f"{s_adk['success_rate']}%", f"{s_adk['successful_queries']}/30 queries")
        col3.metric("Relative Accuracy Gain", b_data["relative_accuracy_gain"], delta_color="normal")

        st.table(pd.DataFrame({
            "Capability": ["Task Completion Rate", "Verification Layer", "Error Recovery Mechanism", "Mean Latency"],
            "Single-Agent Baseline": [f"{s_base['success_rate']}%", s_base["verification_layer"], s_base["error_recovery"], f"{s_base['mean_latency_ms']} ms"],
            "Google ADK Multi-Agent": [f"{s_adk['success_rate']}%", s_adk["verification_layer"], f"Active ({s_adk['error_recovery_rate']}% recovered)", f"{s_adk['mean_latency_ms']} ms"],
        }))
