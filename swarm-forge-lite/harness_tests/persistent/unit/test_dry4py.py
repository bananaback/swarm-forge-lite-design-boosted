"""Unit tests for the dry4py scope, parser, detector, and writer helpers."""

import io
import json
import sys
from pathlib import Path

import pytest
from dry4py.detector import JscpdDetector
from dry4py.errors import (
    DetectorError,
    DetectorUnavailable,
    EmptyScope,
    InvalidDuplicate,
    InvalidRegion,
)
from dry4py.parser import JscpdReportParser
from dry4py.process import SubprocessRunner
from dry4py.values import CodeRegion, Duplicate, DuplicateReport, ScanScope
from dry4py.writer import ConsoleReportWriter


def test_scan_scope_requires_a_path():
    with pytest.raises(EmptyScope, match="at least one path"):
        ScanScope(())


def test_scan_scope_rejects_non_positive_thresholds(tmp_path):
    with pytest.raises(EmptyScope, match="min_lines"):
        ScanScope((tmp_path,), min_lines=0)
    with pytest.raises(EmptyScope, match="min_tokens"):
        ScanScope((tmp_path,), min_tokens=0)


def test_scan_scope_reports_a_missing_path(tmp_path):
    with pytest.raises(EmptyScope, match="missing.py"):
        ScanScope((tmp_path / "missing.py",))


def test_region_and_duplicate_values_refuse_impossible_spans():
    with pytest.raises(InvalidRegion):
        CodeRegion("a.py", 4, 1)
    region = CodeRegion("a.py", 1, 4)
    with pytest.raises(InvalidDuplicate):
        Duplicate(region, region)


def test_report_parser_reads_a_duplicate_pair():
    raw = json.dumps(
        {
            "duplicates": [
                {
                    "firstFile": {"name": "a.py", "start": 1, "end": 4},
                    "secondFile": {"name": "b.py", "start": 2, "end": 5},
                }
            ]
        }
    )
    duplicates = JscpdReportParser().parse(raw)
    assert duplicates == (
        Duplicate(CodeRegion(Path("a.py"), 1, 4), CodeRegion(Path("b.py"), 2, 5)),
    )


def test_report_parser_refuses_invalid_json():
    with pytest.raises(DetectorError, match="not valid JSON"):
        JscpdReportParser().parse("not json")


def test_report_parser_refuses_a_missing_duplicate_list():
    with pytest.raises(DetectorError, match="no duplicate list"):
        JscpdReportParser().parse("{}")


def test_report_parser_refuses_a_malformed_clone():
    with pytest.raises(DetectorError, match="malformed clone entry"):
        JscpdReportParser().parse('{"duplicates": [{"firstFile": {}}]}')


def test_detector_command_passes_the_scope_and_thresholds(tmp_path):
    scope = ScanScope((tmp_path,), min_lines=6, min_tokens=20)
    command = JscpdDetector(None, None)._command(scope, "/output")
    assert command[0] == "jscpd"
    assert command[command.index("--min-lines") + 1] == "6"
    assert command[command.index("--min-tokens") + 1] == "20"
    assert str(tmp_path) in command


def test_subprocess_runner_accepts_status_zero_and_one():
    runner = SubprocessRunner()
    runner.run([sys.executable, "-c", "import sys; sys.exit(0)"])
    runner.run([sys.executable, "-c", "import sys; sys.exit(1)"])


def test_subprocess_runner_refuses_a_failing_status():
    with pytest.raises(DetectorError):
        SubprocessRunner().run([sys.executable, "-c", "import sys; sys.exit(3)"])


def test_subprocess_runner_refuses_a_missing_command():
    with pytest.raises(DetectorUnavailable, match="command not found"):
        SubprocessRunner().run(["definitely-not-a-real-command-xyz"])


def test_writer_reports_a_clean_scan():
    stream = io.StringIO()
    ConsoleReportWriter(stream).write(DuplicateReport(()))
    assert stream.getvalue() == "No duplicate candidates found.\n"


def test_writer_lists_positions_and_the_count():
    stream = io.StringIO()
    report = DuplicateReport(
        (Duplicate(CodeRegion("a.py", 1, 4), CodeRegion("b.py", 1, 4)),)
    )
    ConsoleReportWriter(stream).write(report)
    output = stream.getvalue()
    assert "a.py:1-4" in output
    assert "b.py:1-4" in output
    assert "1 duplicate candidate(s)." in output
