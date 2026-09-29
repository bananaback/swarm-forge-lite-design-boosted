"""ruff4py -- Python code-quality check for the pack.

A thin wrapper over `ruff check` that pins the cache to the wiring artifacts
root and defaults the config to the pack's `ruff.toml`. Every other argument
passes through to ruff unchanged.

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
    RuffConfig,
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
    "RuffConfig",
    "RuffInvocation",
    "SubprocessChecker",
    "ToolLocator",
    "ToolUnavailable",
    "UsageWriter",
]
