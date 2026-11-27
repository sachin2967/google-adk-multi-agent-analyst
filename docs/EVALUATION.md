# Evaluation and limits

## What is measured today

1. **Unit and integration tests (32).** ADK graph construction, API validation,
   metric semantics, parameter rejection, read-only SQLite, service limits, and a real
   MCP stdio round trip. The end-to-end ADK-to-MCP-to-SQLite test uses a **scripted
   model**, so it validates orchestration and tool transport, not LLM quality.
2. **Tool regression (4 of 4).** `python scripts/run_benchmark.py` compares MCP
   aggregates with independent SQL on the synthetic fixture and writes
   `tool_regression_report.json` (git-ignored):
   - delivered revenue by category sums to the independent total
   - order counts by status match
   - overall average review matches
   - order counts by state match

## What is not measured

- Natural-language intent accuracy and answer correctness with a real model.
- Latency and cost per question, and behavior under realistic concurrency.
- Any property of real business data; the fixture is synthetic.

## Plan for a live-model evaluation

1. Freeze questions and independently computed answers before any run.
2. Run deterministic, single-agent and multi-agent configurations on the same set.
3. Record answer accuracy, tool-call correctness, latency and provider token counts.
4. Never count scripted-model CI results as model quality.
