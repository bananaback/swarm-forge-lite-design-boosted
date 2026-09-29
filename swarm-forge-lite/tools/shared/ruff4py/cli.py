"""Command line entry point and composition root."""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import wiring  # noqa: E402

from .errors import (  # noqa: E402
    InvalidConfiguration,
    InvalidUsage,
    ToolUnavailable,
)
from .locator import PathToolLocator  # noqa: E402
from .process import SubprocessChecker  # noqa: E402
from .usage import ConsoleUsage  # noqa: E402
from .values import CheckArguments, CheckRequest  # noqa: E402

CONFIG_ENV = "RUFF4PY_CONFIG"


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
        request = CheckRequest(
            arguments,
            resolved.pack_root,
            resolved.artifacts_root,
            os.environ.get(CONFIG_ENV),
        )
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
