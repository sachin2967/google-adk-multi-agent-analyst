"""Unit tests for AST-parsed safe Python execution sandbox."""

import pytest
from src.sandbox.executor import SandboxedPythonExecutor, SecurityViolation


@pytest.fixture
def sandbox():
    return SandboxedPythonExecutor()


def test_safe_math_execution(sandbox):
    code = """
import numpy as np
import pandas as pd
data = [10, 20, 30, 40]
result = np.mean(data)
"""
    success, res, err, _ = sandbox.execute(code)
    assert success is True
    assert res == 25.0
    assert err is None


def test_block_os_import(sandbox):
    code = "import os\nos.system('whoami')"
    success, res, err, _ = sandbox.execute(code)
    assert success is False
    assert "Unauthorized import attempt" in err


def test_block_subprocess_import(sandbox):
    code = "import subprocess\nsubprocess.run(['ls'])"
    success, res, err, _ = sandbox.execute(code)
    assert success is False
    assert "Unauthorized import attempt" in err


def test_block_eval_call(sandbox):
    code = "eval('1 + 1')"
    success, res, err, _ = sandbox.execute(code)
    assert success is False
    assert "Forbidden function invocation" in err


def test_block_file_open(sandbox):
    code = "f = open('test.txt', 'w')"
    success, res, err, _ = sandbox.execute(code)
    assert success is False
    assert "Forbidden function invocation" in err
