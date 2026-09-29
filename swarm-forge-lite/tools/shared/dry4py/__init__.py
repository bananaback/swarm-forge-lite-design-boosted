"""dry4py -- duplicate-code report for Python projects.

Finds duplicated regions with jscpd and prints each pair as two file and
line ranges. Report-only: it never fails on duplicates.

The parts:

1. State the request and the result -- `values.py`
2. Name the collaborators the domain needs -- `contracts.py`
3. Invoke the detector -- `process.py`, `detector.py`, `parser.py`
4. Present the result -- `writer.py`
5. Run the use case -- `command.py`, `cli.py`
"""

from .command import DuplicateReportCommand
from .contracts import DuplicateDetector, ProcessRunner, ReportWriter
from .detector import JscpdDetector
from .errors import (
    DetectorError,
    DetectorUnavailable,
    EmptyScope,
    InvalidDuplicate,
    InvalidRegion,
)
from .parser import JscpdReportParser
from .process import SubprocessRunner
from .values import CodeRegion, Duplicate, DuplicateReport, ScanScope
from .writer import ConsoleReportWriter

__all__ = [
    "CodeRegion",
    "ConsoleReportWriter",
    "DetectorError",
    "DetectorUnavailable",
    "Duplicate",
    "DuplicateDetector",
    "DuplicateReport",
    "DuplicateReportCommand",
    "EmptyScope",
    "InvalidDuplicate",
    "InvalidRegion",
    "JscpdDetector",
    "JscpdReportParser",
    "ProcessRunner",
    "ReportWriter",
    "ScanScope",
    "SubprocessRunner",
]
