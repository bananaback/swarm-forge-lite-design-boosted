"""ruff4py -- Python code-quality check for the pack.

A thin wrapper over `ruff check` that pins the cache to the wiring artifacts
root. Ruff discovers the repository config from each file's own directory, so
the wrapper injects no config. Every other argument passes through to ruff
unchanged.

The four actions:

1. State the request and the invocation -- `values.py`
2. Name the collaborators the wrapper needs -- `contracts.py`
3. Reach the environment -- `locator.py`, `process.py`, `usage.py`
4. Compose and run -- `cli.py`
"""

from .contracts import CodeChecker, ToolLocator, UsageWriter
from .errors import InvalidConfiguration, InvalidUsage, ToolUnavailable
from .locator import PathToolLocator
from .process import SubprocessChecker
from .usage import ConsoleUsage
from .values import (
    CacheDirectory,
    CheckArguments,
    CheckRequest,
    RuffInvocation,
)

__all__ = [
    "CacheDirectory",
    "CheckArguments",
    "CheckRequest",
    "CodeChecker",
    "ConsoleUsage",
    "InvalidConfiguration",
    "InvalidUsage",
    "PathToolLocator",
    "RuffInvocation",
    "SubprocessChecker",
    "ToolLocator",
    "ToolUnavailable",
    "UsageWriter",
]
