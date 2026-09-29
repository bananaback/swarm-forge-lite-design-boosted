"""How the LCOV file is produced."""

import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from .errors import ToolError


class CoverageProvider(Protocol):
    """A port: a source that yields an LCOV file at `lcov`."""

    lcov: Path

    def produce(self) -> None: ...


@dataclass
class PytestCoverage:
    """Run the default coverage.py + pytest pipeline."""

    lcov: Path
    tests: tuple[str, ...]
    artifacts: Path

    def produce(self) -> None:
        self.artifacts.mkdir(parents=True, exist_ok=True)
        self.lcov.unlink(missing_ok=True)
        env = {
            **os.environ,
            "COVERAGE_FILE": str(self.artifacts / ".coverage"),
        }
        run = [
            sys.executable,
            "-m",
            "coverage",
            "run",
            "-m",
            "pytest",
            "-p",
            "no:cacheprovider",
            *self.tests,
        ]
        if subprocess.run(run, env=env).returncode != 0:
            print("crap4py: tests failed; reporting what ran", file=sys.stderr)
        subprocess.run(
            [sys.executable, "-m", "coverage", "lcov", "-o", str(self.lcov)],
            env=env,
        )


@dataclass
class CommandCoverage:
    """Run a caller-supplied command; `{lcov}` is replaced by the path."""

    lcov: Path
    command: str

    def produce(self) -> None:
        proc = subprocess.run(
            self.command.replace("{lcov}", str(self.lcov)), shell=True
        )
        if proc.returncode != 0:
            print(
                f"crap4py: coverage command exited {proc.returncode}",
                file=sys.stderr,
            )


@dataclass
class ExistingCoverage:
    """Read an LCOV file that already exists."""

    lcov: Path

    def produce(self) -> None:
        if not self.lcov.exists():
            raise ToolError(f"missing LCOV file {self.lcov}")
