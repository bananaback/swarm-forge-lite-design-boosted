"""Where function complexity comes from."""

import json
import os
import subprocess
import sys
from typing import Protocol

from .errors import ToolError
from .function import Function


class ComplexitySource(Protocol):
    """A port: the functions under analysis and their complexity."""

    def functions(self) -> tuple[Function, ...]: ...


def run_radon(roots: tuple[str, ...]) -> str:
    """Run `radon cc -j` over the roots and return its stdout."""
    proc = subprocess.run(
        [sys.executable, "-m", "radon", "cc", "-j", *roots],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise ToolError(f"radon failed: {proc.stderr.strip()}")
    return proc.stdout


def parse_radon_report(stdout: str) -> tuple[Function, ...]:
    """Translate `radon cc -j` JSON into the functions it describes."""
    try:
        data = json.loads(stdout or "{}")
    except json.JSONDecodeError as error:
        raise ToolError(f"cannot parse radon output: {error}") from error
    return tuple(
        Function(
            entry["name"],
            os.path.normpath(path),
            entry["lineno"],
            entry["endline"],
            entry["complexity"],
        )
        for path, entries in data.items()
        if isinstance(entries, list)
        for entry in entries
        if entry.get("type") in {"function", "method"}
    )


class RadonComplexity:
    """Adapter over `radon cc -j`."""

    def __init__(self, roots: tuple[str, ...]):
        self._roots = roots

    def functions(self) -> tuple[Function, ...]:
        return parse_radon_report(run_radon(self._roots))
