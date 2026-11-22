"""The analytics tool layer only permits fixed dataframe operations."""

import pandas as pd
import pytest

from src.sandbox.executor import SandboxedPythonExecutor


def test_monthly_growth_operation():
    executor = SandboxedPythonExecutor()
    frame = pd.DataFrame({"monthly_revenue": [100.0, 125.0, 100.0]})
    ok, result, error = executor.execute_operation("monthly_growth", frame)
    assert ok and error is None
    assert result["mom_growth_pct"].iloc[1] == 25.0
    assert result["mom_growth_pct"].iloc[2] == pytest.approx(-20.0)
    assert "mom_growth_pct" not in frame.columns


def test_arbitrary_python_is_never_executed(tmp_path):
    marker = tmp_path / "should_not_exist"
    code = f"open({str(marker)!r}, 'w').write('executed')"
    ok, _result, error, _ = SandboxedPythonExecutor().execute(code)
    assert not ok
    assert "disabled" in error
    assert not marker.exists()


def test_unknown_operation_is_rejected():
    ok, _, error = SandboxedPythonExecutor().execute_operation(
        "arbitrary", pd.DataFrame()
    )
    assert not ok
    assert "Unsupported" in error
