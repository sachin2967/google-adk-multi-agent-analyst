"""Exact tool-intent and structured-answer scoring, without an LLM judge."""

import json
import math

DEFAULT_ARGS = {"group_by": "none", "order_status": None, "state": None, "limit": 20}
ANSWER_FORMAT = """Return ONLY a JSON object, no Markdown. For supported questions:
{"supported": true, "metric": "orders", "group_by": "none", "records": [{"value": 123}], "reason": ""}.
Use the actual metric, grouping and records from the tool, include group_value for grouped results.
For unsupported questions: {"supported": false, "reason": "explain limitation"}.
Always call the commerce analysis tool for supported questions; never invent values.
The available metrics are revenue, orders, average_review, average_delivery_days.
Groupings: none, category, state, month, status; filters: order_status and two-letter state.
Revenue defaults to delivered unless status is explicitly requested or grouped by status.
All orders include every status unless filtered. Do not execute SQL, Python, write data or expose individual rows."""


def records_equal(actual, expected) -> bool:
    if not isinstance(actual, list) or len(actual) != len(expected):
        return False
    if any(not isinstance(row, dict) for row in actual):
        return False
    actual = sorted(actual, key=lambda row: str(row.get("group_value", "")))
    expected = sorted(expected, key=lambda row: str(row.get("group_value", "")))
    for row, truth in zip(actual, expected):
        if set(row) != set(truth):
            return False
        for key, value in truth.items():
            found = row[key]
            if isinstance(value, (int, float)):
                if isinstance(found, bool) or not isinstance(found, (int, float)):
                    return False
                if isinstance(value, int):
                    if found != value:
                        return False
                else:
                    try:
                        if not math.isfinite(found) or not math.isclose(
                            found, value, rel_tol=1e-6, abs_tol=0.01
                        ):
                            return False
                    except OverflowError:
                        return False
            elif found != value:
                return False
    return True


def score_response(case: dict, result: dict, expected: list | None) -> dict:
    calls = result.get("tool_calls", [])
    metric_calls = [call for call in calls if call["name"].endswith("analyze_commerce")]
    allowed = all(
        call["name"].endswith(("analyze_commerce", "get_analytics_schema"))
        for call in calls
    )
    try:
        answer = json.loads(result["answer"])
        if not isinstance(answer, dict):
            raise TypeError("Object required")
    except (ValueError, KeyError, TypeError):
        answer = None
    valid_json_object = answer is not None
    answer = answer or {}
    supported = case["args"] is not None
    if supported:
        truth_args = {**DEFAULT_ARGS, **case["args"]}
        intent = bool(metric_calls) and all(
            {**DEFAULT_ARGS, **call["args"]} == truth_args for call in metric_calls
        )
        numeric = (
            answer.get("supported") is True
            and answer.get("metric") == truth_args["metric"]
            and answer.get("group_by") == truth_args["group_by"]
            and records_equal(answer.get("records"), expected)
        )
        refusal = None
    else:
        intent, numeric = not metric_calls, None
        reason = answer.get("reason")
        refusal = (
            answer.get("supported") is False
            and isinstance(reason, str)
            and bool(reason.strip())
            and not metric_calls
        )
    return {
        "valid_json_object": valid_json_object,
        "allowlisted_calls_only": allowed,
        "tool_intent_correct": intent,
        "structured_result_correct": numeric,
        "unsupported_refusal_correct": refusal,
        "passed": allowed and intent and (numeric if supported else refusal),
    }
