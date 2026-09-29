"""Adapter for running an external command."""

import subprocess
from collections.abc import Sequence

from .errors import DetectorError, DetectorUnavailable

ACCEPTED_EXIT_CODES = (0, 1)


class SubprocessRunner:
    """Runs a command in a child process, capturing its output."""

    def run(self, argv: Sequence[str]) -> None:
        try:
            proc = subprocess.run(tuple(argv), capture_output=True, text=True)
        except FileNotFoundError as error:
            raise DetectorUnavailable("command not found: " + argv[0]) from error
        if proc.returncode not in ACCEPTED_EXIT_CODES:
            detail = proc.stderr.strip() or "exit " + str(proc.returncode)
            raise DetectorError(detail)
