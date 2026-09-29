"""Command line entry point."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "shared"))

import wiring  # noqa: E402

from .complexity import RadonComplexity  # noqa: E402
from .errors import ToolError  # noqa: E402
from .providers import (  # noqa: E402
    CommandCoverage,
    CoverageProvider,
    ExistingCoverage,
    PytestCoverage,
)
from .tool import CrapTool  # noqa: E402


def parse_args(argv):
    parser = argparse.ArgumentParser(
        prog="crap4py",
        description="CRAP report for Python projects (radon + coverage.py).",
    )
    parser.add_argument(
        "--source-root",
        action="append",
        default=[],
        help="source root; repeatable (default: wiring source_roots)",
    )
    parser.add_argument(
        "--test-path",
        action="append",
        default=[],
        help="test path for the default coverage run; repeatable",
    )
    parser.add_argument(
        "--lcov",
        help="LCOV file (default: <artifacts>/coverage.lcov)",
    )
    parser.add_argument(
        "--use-existing-coverage",
        action="store_true",
        help="read the LCOV file without running coverage",
    )
    parser.add_argument(
        "--coverage-command",
        help="command producing the LCOV file; {lcov} is its path",
    )
    parser.add_argument(
        "filters",
        nargs="*",
        help="only report files whose path contains one of these fragments",
    )
    return parser.parse_args(argv)


def coverage_provider(args, resolved) -> CoverageProvider:
    """Choose the coverage strategy from the flags."""
    lcov = Path(args.lcov) if args.lcov else resolved.artifacts_root / "coverage.lcov"
    if args.use_existing_coverage:
        return ExistingCoverage(lcov)
    if args.coverage_command:
        return CommandCoverage(lcov, args.coverage_command)
    return PytestCoverage(lcov, tuple(args.test_path), resolved.artifacts_root)


def main(argv) -> int:
    args = parse_args(argv)
    resolved = wiring.load()
    roots = tuple(args.source_root) or tuple(
        str(path) for path in resolved.source_roots
    )
    tool = CrapTool(
        RadonComplexity(roots),
        coverage_provider(args, resolved),
        tuple(args.filters),
    )
    try:
        return tool.run()
    except ToolError as error:
        print(f"crap4py: {error}", file=sys.stderr)
        return 1
