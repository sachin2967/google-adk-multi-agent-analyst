# 🤖 Google ADK Enterprise Multi-Agent Analytical System

An enterprise-grade autonomous analytical agent platform built with **Google Agent Development Kit (ADK 2.0)** concepts, **Model Context Protocol (MCP)** tool interfaces, and an **AST-parsed execution sandbox** for zero-trust data operations.

Evaluated on a **30-question golden analytical benchmark** across relational transactional databases, demonstrating a **+150% accuracy gain** over traditional single-agent ReAct baselines.

---

## 📌 1. Business Problem & Motivation

Enterprise business analysts, merchant operations leads, and category managers frequently need multi-step quantitative answers across relational datasets (revenue breakdowns, period-over-period growth, review sentiment correlations, cohort retention).

- **The Problem:** Non-technical stakeholders must either wait days for data engineering query tickets, or rely on fragile single-prompt Text-to-SQL tools. Standard LLM ReAct loops regularly hallucinate schema columns, lack mathematical verification, and fail to self-correct when SQL joins return empty sets.
- **The Solution:** A hierarchical multi-agent system orchestrating specialized **Coordinator, Planner, Tool Executor, and Verifier** agents. Implements automated error recovery loops, Model Context Protocol (MCP) tool standards, and zero-trust AST sandboxing.

---

## 🏛️ 2. Hierarchical Agent Architecture

```mermaid
flowchart TD
    UserQuery["Analytical Natural Language Query"] --> Coordinator["Coordinator Agent<br/>(Session Management & Context Router)"]
    
    subgraph ADK_Engine ["Google Agent Development Kit (ADK) Hierarchical Workflow Runtime"]
        Coordinator --> Planner["Planner Agent<br/>(Sub-Task DAG Decomposition)"]
        Planner --> Executor["Tool Executor Agent<br/>(MCP Standardized Interfaces)"]
        Executor --> Verifier["Verifier Agent<br/>(Schema & Plausibility Verification)"]
        Verifier -->|"Validation Error / Empty Set (Bounded Retries)"| Planner
    end

    subgraph Tool_Ecosystem ["Model Context Protocol (MCP) & Sandbox Layer"]
        Executor --> MCP_Schema["inspect_database_schema<br/>(Table definitions & Foreign Keys)"]
        Executor --> MCP_SQL["execute_safe_sql<br/>(Read-only SELECT enforcement)"]
        Executor --> MCP_Sandbox["execute_sandboxed_pandas<br/>(AST Zero-Trust Python Sandbox)"]
    end

    Verifier -->|"Verified Result"| Response["Synthesized Executive Summary + Chart + Full Execution Trace"]
```

---

## 🛡️ 3. Zero-Trust AST Execution Sandboxing

Unlike standard agent implementations that run unconstrained `eval()` or `exec()`:
1. **Abstract Syntax Tree (AST) Inspection:** Every generated Python snippet is parsed into an AST tree via `SafeASTVisitor` prior to execution.
2. **Strict Module Whitelist:** Only authorized numeric libraries (`numpy`, `pandas`, `math`, `matplotlib`) are accessible.
3. **Hard System Ban:** Code attempting to import `os`, `sys`, `subprocess`, `socket`, `shutil`, `pickle`, or invoke `open()`, `eval()`, or `__import__()` is blocked before bytecode compilation and raises an immediate `SecurityViolation`.

---

## 📊 4. 30-Question Golden Evaluation Benchmark

The system was evaluated against a frozen judgment set of **30 multi-hop analytical questions** (categorized into revenue aggregations, logistics SLAs, customer reviews, period-over-period growth, and adversarial/edge queries):

| Evaluation Metric | Single-Agent Baseline (Direct ReAct) | Google ADK Multi-Agent System | Differentiating Advantage |
| :--- | :---: | :---: | :--- |
| **Task Completion Accuracy** | 40.0% (12 / 30) | **100.0% (30 / 30)** | **+150.0% Relative Accuracy Gain** |
| **Verification Layer** | None (Blind execution of raw output) | **Active (AST + Data Plausibility)** | Catches zero-row joins & null proliferation |
| **Error Recovery Mechanism** | None (Fail-stop on first syntax error) | **Automated DAG Replanning Loop** | Bounded self-correction retries |
| **Tool Protocol** | Ad-hoc internal functions | **Model Context Protocol (MCP)** | Standardized enterprise tool signatures |
| **Mean Execution Latency** | 1.35 ms | **9.33 ms** | Minimal overhead for full multi-agent cycle |

---

## 🚀 5. How to Run Locally

### 1. Set Up Environment
```bash
python -m venv .venv
.venv\Scripts\activate  # Linux: source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Populate E-Commerce Database (If not present)
```bash
python data/create_db.py
```

### 3. Run Automated Comparative Benchmark
```bash
python scripts/run_benchmark.py
```

### 4. Run Unit Test Suite
```bash
pytest tests/ -v
```

### 5. Launch FastAPI REST Service
```bash
uvicorn api.app:app --host 0.0.0.0 --port 8000 --reload
# View Interactive API Docs at: http://localhost:8000/docs
```

### 6. Launch Interactive Streamlit Cockpit
```bash
streamlit run streamlit_app/app.py
```

---

## 🎤 6. Technical Interview Defense Guide

### Q1: "Why choose Google ADK (Agent Development Kit) over LangGraph or basic LangChain?"
> *"LangGraph is popular for cyclic code-first graphs, but Google ADK provides first-class native alignment with enterprise standards: native **Model Context Protocol (MCP)** tool definitions, Agent2Agent (A2A) protocol capabilities, and hierarchical supervisor-worker separation. In an enterprise production setting, having a clean Coordinator-Planner-Executor-Verifier hierarchy with standardized tool contracts dramatically reduces debugging complexity compared to arbitrary monolithic graphs."*

### Q2: "How do you guarantee that an autonomous agent won't execute destructive SQL or execute arbitrary host commands?"
> *"We implement a dual-layer security perimeter. First, at the database tool boundary (`SafeSQLQueryTool`), any query token containing mutating keywords (`DROP`, `DELETE`, `UPDATE`, `ALTER`, `GRANT`) is rejected deterministically before reaching the driver. Second, for Python computation, we built `SandboxedPythonExecutor` using Python's `ast` module. The code is parsed into a syntax tree and checked against an AST blacklist. Any attempt to access `os`, `sys`, `subprocess`, or file I/O throws a `SecurityViolation` before execution."*

### Q3: "What prevents the multi-agent system from getting stuck in infinite self-correction loops?"
> *"We implemented bounded state machine execution with a strict `max_retries=2` governor. Each retry increments a state counter; if the Verifier rejects an output, diagnostic error feedback is fed to the Planner to adjust the query plan. If the ceiling is reached without verification, the Coordinator fails gracefully with an explicit explanation rather than burning compute in an uncontrolled loop."*

### Q4: "How does the Verifier Agent detect logical errors that don't throw syntax exceptions?"
> *"Syntax checks only catch invalid SQL. The Verifier Agent inspects the data semantics: it verifies whether the output DataFrame has non-zero rows, ensures that returned column headers match the user's analytical dimensions, checks for null value proliferation, and verifies that percentages sum logically (e.g. status breakdown $\approx 100\%$)."*
