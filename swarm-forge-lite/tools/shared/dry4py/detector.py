"""Adapter that drives the jscpd duplicate detector."""

import tempfile
from pathlib import Path

from .contracts import ProcessRunner
from .errors import DetectorError
from .parser import JscpdReportParser
from .values import DuplicateReport, ScanScope

EXECUTABLE = "jscpd"
MODE = "weak"
REPORT_NAME = "jscpd-report.json"


class JscpdDetector:
    """Detects duplicates by invoking jscpd and translating its report."""

    def __init__(self, runner: ProcessRunner, parser: JscpdReportParser):
        self._runner = runner
        self._parser = parser

    def detect(self, scope: ScanScope) -> DuplicateReport:
        with tempfile.TemporaryDirectory() as output:
            self._runner.run(self._command(scope, output))
            report = Path(output) / REPORT_NAME
            if not report.exists():
                raise DetectorError("detector produced no report")
            return DuplicateReport(self._parser.parse(report.read_text()))

    def _command(self, scope: ScanScope, output: str) -> tuple:
        return (
            EXECUTABLE,
            "--format",
            "python",
            "--min-lines",
            str(scope.min_lines),
            "--min-tokens",
            str(scope.min_tokens),
            "--mode",
            MODE,
            "--reporters",
            "json",
            "--output",
            output,
            "--workers",
            "4",
            "--silent",
            *(str(path) for path in scope.paths),
        )
