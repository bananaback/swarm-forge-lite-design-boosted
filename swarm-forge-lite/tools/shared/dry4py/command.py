"""The tool's single use case: detect duplicates, then report them."""

from .contracts import DuplicateDetector, ReportWriter
from .values import ScanScope


class DuplicateReportCommand:
    """Runs one duplicate report, from scan scope to rendered output."""

    def __init__(self, detector: DuplicateDetector, writer: ReportWriter):
        self._detector = detector
        self._writer = writer

    def run(self, scope: ScanScope) -> None:
        report = self._detector.detect(scope)
        self._writer.write(report)
