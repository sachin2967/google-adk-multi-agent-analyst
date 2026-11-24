"""Prepare offline ground truth or explicitly run bounded live-model comparisons."""

import argparse
import asyncio
import hashlib
import json
import os
import sqlite3
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.evaluation.live import ANSWER_FORMAT, score_response
from src.tools.mcp_tools import DEFAULT_DB, _connect, query_metrics


def load_cases():
    path = ROOT / "data/analyst_questions_v1.json"
    frozen = json.loads(path.read_text(encoding="utf-8"))
    return frozen, hashlib.sha256(path.read_bytes()).hexdigest()


def expected_records(case):
    if case["sql"] is None:
        return None
    with _connect(DEFAULT_DB) as connection:
        connection.row_factory = sqlite3.Row
        return [dict(row) for row in connection.execute(case["sql"]).fetchall()]


async def live_case(question, strategy):
    from google.adk.agents import LlmAgent
    from google.adk.apps import App

    from src.agents.adk_system import _mcp_toolset, build_app
    from src.agents.service import TIMEOUT_SECONDS, _run_agent

    if strategy == "multi":
        app = build_app()
        root = app.root_agent
        root.sub_agents[-1].instruction += "\n" + ANSWER_FORMAT
        final_author = "analytics_verifier"
    else:
        configured = build_app()  # Resolve exactly the same provider/model as multi.
        model = configured.root_agent.sub_agents[0].model
        final_author = "single_analytics"
        agent = LlmAgent(
            name=final_author,
            model=model,
            instruction=ANSWER_FORMAT,
            tools=[_mcp_toolset()],
            generate_content_config={"max_output_tokens": 2048},
        )
        app = App(name="commerce_analytics", root_agent=agent)
    async with asyncio.timeout(TIMEOUT_SECONDS):
        return await _run_agent(
            question, app=app, final_author=final_author, capture_trace=True
        )


async def evaluate(args):
    frozen, digest = load_cases()
    selected = [
        case
        for case in frozen["cases"]
        if args.split == "all" or case["split"] == args.split
    ][: args.max_cases]
    if args.live and not os.getenv("ANALYST_MODEL", "").strip():
        raise RuntimeError(
            "Configure ANALYST_MODEL and its provider credential before --live."
        )
    results = []
    for case_index, case in enumerate(selected):
        expected = expected_records(case)
        started = time.perf_counter()
        if case["args"] is not None:
            deterministic = query_metrics(**case["args"])
            result = {
                "answer": json.dumps({"supported": True, **deterministic}),
                "tool_calls": [{"name": "analyze_commerce", "args": case["args"]}],
            }
            results.append(
                {
                    "id": case["id"],
                    "strategy": "oracle_tool_contract",
                    "elapsed_ms": (time.perf_counter() - started) * 1000,
                    **score_response(case, result, expected),
                }
            )
        if args.live:
            strategies = (
                ["single", "multi"] if case_index % 2 == 0 else ["multi", "single"]
            )
            for strategy in strategies:
                started = time.perf_counter()
                try:
                    result = await live_case(case["question"], strategy)
                    row = {
                        **score_response(case, result, expected),
                        "reported_token_usage": result["reported_token_usage"],
                        "event_count": result["event_count"],
                        "tool_calls": result["tool_calls"],
                        "answer": result["answer"],
                    }
                except Exception as exc:  # noqa: BLE001 -- record provider failure without leaking exception text
                    row = {"passed": False, "error_type": type(exc).__name__}
                results.append(
                    {
                        "id": case["id"],
                        "strategy": strategy,
                        "elapsed_ms": (time.perf_counter() - started) * 1000,
                        **row,
                    }
                )
                # Incremental safe output preserves completed trials on interruption.
                args.output.parent.mkdir(parents=True, exist_ok=True)
                args.output.write_text(
                    json.dumps({"partial": True, "results": results}, indent=2) + "\n",
                    encoding="utf-8",
                )
    report = {
        "protocol": frozen["version"],
        "questions_sha256": digest,
        "database_sha256": hashlib.sha256(DEFAULT_DB.read_bytes()).hexdigest(),
        "live_provider_executed": args.live,
        "model": os.getenv("ANALYST_MODEL", "") if args.live else None,
        "split": args.split,
        "case_count": len(selected),
        "results": results,
        "limitations": [
            "Small authored synthetic benchmark; no independent human review or real business dataset.",
            "Deterministic baseline receives oracle tool arguments; it is not a natural-language system.",
            "Structured exact-result scoring does not judge prose usefulness or general safety.",
            "One run per strategy/case; token usage is provider reported, no invented monetary cost.",
            "8 LLM calls and 60 seconds per run; billed cancellation/retries are provider-dependent.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "live": args.live,
                "cases": len(selected),
                "results": len(results),
                "passed": sum(r["passed"] for r in results),
                "output": str(args.output),
            },
            indent=2,
        )
    )
    return int(any(not row["passed"] for row in results))


def main():
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env", override=False)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--live",
        action="store_true",
        help="Explicitly enable provider calls (may incur cost).",
    )
    parser.add_argument(
        "--split", choices=["development", "test", "all"], default="development"
    )
    parser.add_argument("--max-cases", type=int, default=2)
    parser.add_argument(
        "--output", type=Path, default=ROOT / "evaluation/analyst_preflight.json"
    )
    args = parser.parse_args()
    if not 1 <= args.max_cases <= 12:
        parser.error("--max-cases must be 1..12")
    return asyncio.run(evaluate(args))


if __name__ == "__main__":
    raise SystemExit(main())
