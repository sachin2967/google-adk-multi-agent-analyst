import copy
import json

import pytest

from src.evaluation.live import records_equal, score_response


def test_numeric_comparison_rejects_missing_duplicate_extra_and_nonfinite_records():
    truth = [{"group_value": "A", "value": 10.12}, {"group_value": "B", "value": 2}]
    assert records_equal(list(reversed(truth)), truth)
    assert not records_equal(truth[:1], truth)
    assert not records_equal([truth[0], truth[0]], truth)
    assert not records_equal(
        [{"group_value": "A", "value": float("nan")}, truth[1]], truth
    )
    assert not records_equal(
        [{"group_value": "A", "value": 10.12, "invented": 3}, truth[1]], truth
    )


def test_correct_number_with_wrong_filters_is_not_correct():
    case = {"args": {"metric": "orders", "state": "MH"}}
    result = {
        "answer": json.dumps(
            {
                "supported": True,
                "metric": "orders",
                "group_by": "none",
                "records": [{"value": 12}],
            }
        ),
        "tool_calls": [
            {
                "name": "commerce_analyze_commerce",
                "args": {"metric": "orders", "state": "KA"},
            }
        ],
    }
    score = score_response(case, result, [{"value": 12}])
    assert score["structured_result_correct"]
    assert not score["passed"]


def test_order_counts_require_exact_values():
    assert not records_equal([{"value": 12.001}], [{"value": 12}])


def test_unsupported_requires_explicit_refusal_and_no_metric_call():
    result = {
        "answer": json.dumps({"supported": False, "reason": "Writes unavailable"}),
        "tool_calls": [],
    }
    assert score_response({"args": None}, result, None)["passed"]
    wrong = copy.deepcopy(result)
    wrong["tool_calls"].append(
        {"name": "analyze_commerce", "args": {"metric": "orders"}}
    )
    assert not score_response({"args": None}, wrong, None)["passed"]


@pytest.mark.parametrize("answer", ["not JSON", "[]", "null", "{}"])
def test_invalid_answer_never_passes(answer):
    assert not score_response(
        {"args": None}, {"answer": answer, "tool_calls": []}, None
    )["passed"]
