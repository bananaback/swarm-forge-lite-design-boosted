"""Command line entry point and composition root."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import wiring

from .errors import (
    InvalidConfiguration,
    InvalidUsage,
    ToolUnavailable,
)
from .locator import PathToolLocator
from .process import SubprocessChecker
from .usage import ConsoleUsage
from .values import CheckArguments, CheckRequest


def parse_args(argv) -> CheckArguments:
    return CheckArguments(tuple(argv))


def main(argv) -> int:
    arguments = parse_args(argv)
    try:
        if arguments.requests_help():
            ConsoleUsage(sys.stdout).show()
            return 0
        if arguments.mentions_verb():
            raise InvalidUsage("`check` is already supplied; run `ruff4py <paths>`")
        executable = PathToolLocator().locate()
        resolved = wiring.load()
        request = CheckRequest(arguments, resolved.artifacts_root)
        request.prepare()
        return SubprocessChecker().check(request.invocation(executable))
    except (
        InvalidUsage,
        InvalidConfiguration,
        ToolUnavailable,
        wiring.WiringError,
    ) as error:
        print("ruff4py: " + str(error), file=sys.stderr)
        return 2
