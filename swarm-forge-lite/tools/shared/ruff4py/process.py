"""Adapter that runs the linter in a child process."""

import subprocess

from .errors import ToolUnavailable
from .values import RuffInvocation


class SubprocessChecker:
    """Runs an invocation with the OS subprocess, passing its status through."""

    def check(self, invocation: RuffInvocation) -> int:
        try:
            return subprocess.call(invocation.as_list())
        except OSError as error:
            raise ToolUnavailable("cannot run ruff: " + str(error)) from error
