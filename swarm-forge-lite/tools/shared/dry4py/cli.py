"""Command line entry point and composition root."""

import argparse
import sys
from pathlib import Path

from .command import DuplicateReportCommand
from .detector import JscpdDetector
from .errors import DetectorError, DetectorUnavailable, EmptyScope
from .parser import JscpdReportParser
from .process import SubprocessRunner
from .values import ScanScope
from .writer import ConsoleReportWriter


def parse_args(argv):
    parser = argparse.ArgumentParser(
        prog="dry4py",
        description="Duplicate-code report for Python projects (jscpd).",
    )
    parser.add_argument("paths", nargs="+", help="files or directories to scan")
    parser.add_argument(
        "--min-lines",
        type=int,
        default=4,
        help="minimum clone size in lines (default: 4)",
    )
    parser.add_argument(
        "--min-tokens",
        type=int,
        default=50,
        help="minimum clone size in tokens (default: 50)",
    )
    return parser.parse_args(argv)


def main(argv) -> int:
    args = parse_args(argv)
    try:
        scope = ScanScope(
            tuple(Path(path) for path in args.paths),
            min_lines=args.min_lines,
            min_tokens=args.min_tokens,
        )
        detector = JscpdDetector(SubprocessRunner(), JscpdReportParser())
        DuplicateReportCommand(detector, ConsoleReportWriter(sys.stdout)).run(scope)
    except (EmptyScope, DetectorUnavailable, DetectorError) as error:
        print("dry4py: " + str(error), file=sys.stderr)
        return 1
    return 0
