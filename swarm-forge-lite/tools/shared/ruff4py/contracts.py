"""Ports the wrapper defines for its outside dependencies."""

from pathlib import Path
from typing import Protocol

from .values import RuffInvocation


class CodeChecker(Protocol):
    """Answers one invocation with the linter's exit status."""

    def check(self, invocation: RuffInvocation) -> int: ...


class ToolLocator(Protocol):
    """Finds the linter executable, raising when it is missing."""

    def locate(self) -> Path: ...


class UsageWriter(Protocol):
    """Presents the wrapper's usage text."""

    def show(self) -> None: ...
