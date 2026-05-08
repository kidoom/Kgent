"""Integration test: verify editable install works (C8)

These tests run pip in a subprocess. Skipped by default — run with:
  pytest -m external tests/integration/test_pip_install.py
"""

import subprocess
import sys

import pytest


@pytest.mark.external
def test_editable_install():
    """pip install -e . succeeds in current environment."""
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-e", "."],
        capture_output=True,
        text=True,
        cwd=".",
    )
    assert result.returncode == 0, f"pip install failed:\n{result.stderr}"


@pytest.mark.external
def test_import_after_install():
    """After install, 'from kagent import ...' works in a fresh subprocess."""
    result = subprocess.run(
        [sys.executable, "-c", "from kagent import SimpleAgent, AgentLLM, Config; print('OK')"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert result.stdout.strip() == "OK"
