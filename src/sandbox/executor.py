"""Safe, fixed dataframe transformations for the local analytics demo.

This module deliberately does not execute generated Python. AST inspection is
not a security boundary for Python's object model; callers select from a small
set of trusted operations implemented in this module instead.
"""

from typing import Any

import pandas as pd


class SecurityViolation(Exception):
    """Raised when a caller requests arbitrary code execution."""


class DataFrameOperationRegistry:
    """Dispatcher for allowlisted dataframe operations.

    No Python source is parsed or passed to ``exec``. Add new transformations
    as explicit functions after reviewing their input and output contract.
    """

    def execute(
        self, code: str, initial_context: dict[str, Any] | None = None
    ) -> tuple[bool, Any, str | None, None]:
        del code, initial_context
        return (
            False,
            None,
            (
                "Arbitrary Python execution is disabled; use an allowlisted dataframe operation."
            ),
            None,
        )

    @staticmethod
    def monthly_growth(df: pd.DataFrame) -> pd.DataFrame:
        """Return a copy with percentage month-over-month revenue change."""
        if not isinstance(df, pd.DataFrame) or "monthly_revenue" not in df.columns:
            raise ValueError("monthly_growth requires a DataFrame with monthly_revenue")
        result = df.copy()
        result["mom_growth_pct"] = result["monthly_revenue"].pct_change() * 100.0
        return result

    def execute_operation(
        self, operation: str, df: pd.DataFrame | None
    ) -> tuple[bool, Any, str | None]:
        if operation != "monthly_growth":
            return False, None, f"Unsupported dataframe operation: {operation}"
        try:
            if df is None:
                raise ValueError("monthly_growth requires a DataFrame")
            return True, self.monthly_growth(df), None
        except (TypeError, ValueError) as exc:
            return False, None, str(exc)


# Historical import alias; this does not execute Python or provide a sandbox.
SandboxedPythonExecutor = DataFrameOperationRegistry
