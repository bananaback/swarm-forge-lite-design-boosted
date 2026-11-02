"""Shared helpers for the harness contract tests.

A contract test may build a pack under `tmp_path`, or shell out to a tool with an
explicit config; none of them may require an installed project. `run_tool` always
starts from the pack root and drops `PACK_PROJECT` unless the test sets it, so a
developer's environment cannot leak into a test.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

PACK = Path(__file__).resolve().parents[1]


def _run(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    environment = dict(os.environ)
    environment.pop("PACK_PROJECT", None)
    environment.update(env or {})
    return subprocess.run(
        [sys.executable, *map(str, args)],
        cwd=PACK,
        capture_output=True,
        text=True,
        env=environment,
        check=False,
    )


@pytest.fixture(name="run_tool")
def run_tool_fixture():
    return _run
