"""AST-parsed execution sandbox for safe Python and Pandas operations.

Enforces zero-trust code inspection, forbidding unsafe syscalls, file writes,
and network operations before code execution.
"""

import ast
import io
import sys
from typing import Any, Dict, Optional, Tuple
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


class SecurityViolation(Exception):
    """Raised when generated code attempts an unauthorized operation."""
    pass


class SafeASTVisitor(ast.NodeVisitor):
    """Inspects AST nodes against an authorized whitelist."""

    FORBIDDEN_MODULES = {
        "os", "sys", "subprocess", "shutil", "socket", "requests", "urllib",
        "importlib", "pickle", "ctypes", "pathlib", "builtin", "builtins"
    }

    FORBIDDEN_CALLS = {
        "eval", "exec", "open", "__import__", "compile", "globals", "locals", "getattr", "setattr"
    }

    def visit_Import(self, node):
        for alias in node.names:
            base_module = alias.name.split(".")[0]
            if base_module in self.FORBIDDEN_MODULES:
                raise SecurityViolation(f"Unauthorized import attempt: '{alias.name}'")
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        if node.module:
            base_module = node.module.split(".")[0]
            if base_module in self.FORBIDDEN_MODULES:
                raise SecurityViolation(f"Unauthorized import attempt: 'from {node.module}'")
        self.generic_visit(node)

    def visit_Call(self, node):
        if isinstance(node.func, ast.Name):
            if node.func.id in self.FORBIDDEN_CALLS:
                raise SecurityViolation(f"Forbidden function invocation: '{node.func.id}()'")
        self.generic_visit(node)


class SandboxedPythonExecutor:
    """Safely executes sanitized Python data manipulation code."""

    def __init__(self):
        self.visitor = SafeASTVisitor()

    def validate_code(self, code: str) -> None:
        """Parses and inspects code AST. Raises SecurityViolation if unsafe."""
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            raise ValueError(f"Syntax error in generated code: {e}")

        self.visitor.visit(tree)

    def execute(
        self, code: str, initial_context: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, Any, Optional[str], Optional[plt.Figure]]:
        """Executes validated code in a restricted scope.

        Returns:
            success: bool
            result: return value or stdout
            error: error message if failed
            figure: matplotlib figure if generated
        """
        try:
            self.validate_code(code)
        except (SecurityViolation, ValueError) as sec_err:
            return False, None, str(sec_err), None

        # Prepare restricted execution globals
        safe_globals = {
            "pd": pd,
            "np": np,
            "plt": plt,
            "print": print,
            "len": len,
            "range": range,
            "round": round,
            "sum": sum,
            "max": max,
            "min": min,
            "dict": dict,
            "list": list,
            "set": set,
            "str": str,
            "int": int,
            "float": float,
            "bool": bool,
        }

        if initial_context:
            safe_globals.update(initial_context)

        # Capture stdout
        old_stdout = sys.stdout
        redirected_output = io.StringIO()
        sys.stdout = redirected_output

        # Clear any prior plots
        plt.close("all")

        try:
            exec_locals = {}
            exec(code, safe_globals, exec_locals)
            output = redirected_output.getvalue().strip()

            # Retrieve result variable if present
            result_val = exec_locals.get("result", output if output else "Executed successfully.")

            # Check if a plot was created
            fig = plt.gcf() if plt.get_fignums() else None

            return True, result_val, None, fig

        except Exception as run_err:
            return False, None, f"Execution Runtime Error: {run_err}", None

        finally:
            sys.stdout = old_stdout
