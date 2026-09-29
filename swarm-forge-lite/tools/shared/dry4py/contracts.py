"""Ports the domain defines for its collaborators."""

from collections.abc import Sequence
from typing import Protocol

from .values import DuplicateReport, ScanScope


class DuplicateDetector(Protocol):
    """Finds duplicated regions within a scan scope."""

    def detect(self, scope: ScanScope) -> DuplicateReport: ...


class ProcessRunner(Protocol):
    """Runs an external command, raising when it cannot complete."""

    def run(self, argv: Sequence[str]) -> None: ...


class ReportWriter(Protocol):
    """Presents a duplicate report to a consumer."""

    def write(self, report: DuplicateReport) -> None: ...
