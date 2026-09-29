"""Orchestrate complexity, coverage, and the report."""

import sys

from .complexity import ComplexitySource
from .coverage import Coverage
from .measurement import Measurement
from .providers import CoverageProvider
from .report import CrapReport


class CrapTool:
    """Join the function list with coverage and show the CRAP table."""

    def __init__(
        self,
        complexity: ComplexitySource,
        coverage: CoverageProvider,
        filters: tuple[str, ...],
    ):
        self._complexity = complexity
        self._coverage = coverage
        self._filters = filters

    def run(self) -> int:
        self._coverage.produce()
        coverage = self._load()
        measurements = tuple(
            Measurement(function, coverage.hits_for(function))
            for function in self._complexity.functions()
            if self._selected(function.path)
        )
        CrapReport(measurements).show()
        return 0

    def _selected(self, path: str) -> bool:
        if not self._filters:
            return True
        return any(fragment in path for fragment in self._filters)

    def _load(self) -> Coverage:
        if not self._coverage.lcov.exists():
            print(
                "crap4py: no coverage data; functions without coverage are marked unmeasured",
                file=sys.stderr,
            )
            return Coverage.empty()
        return Coverage.load(self._coverage.lcov)
