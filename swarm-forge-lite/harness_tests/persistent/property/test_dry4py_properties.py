"""Hypothesis properties for dry4py thresholds, command, and report parsing."""

import io
import json
from pathlib import Path

import pytest
from dry4py.detector import JscpdDetector
from dry4py.errors import EmptyScope
from dry4py.parser import JscpdReportParser
from dry4py.values import CodeRegion, Duplicate, DuplicateReport, ScanScope
from dry4py.writer import ConsoleReportWriter
from hypothesis import assume, given, settings
from hypothesis import strategies as st

NAMES = st.text(alphabet="abc/._", min_size=1, max_size=8)
REGIONS = st.tuples(
    NAMES,
    st.integers(min_value=1, max_value=100),
    st.integers(min_value=1, max_value=100),
)


def _region(name, start, length):
    return CodeRegion(Path(name), start, start + length - 1)


def _json_region(name, region):
    return {"name": name, "start": region.start, "end": region.end}


@settings(max_examples=100, deadline=None)
@given(start=st.integers(min_value=1, max_value=500), length=st.integers(1, 500))
def test_line_count_is_the_inclusive_span(start, length):
    assert _region("a.py", start, length).line_count() == length


@settings(max_examples=100, deadline=None)
@given(
    min_lines=st.integers(min_value=1, max_value=200),
    min_tokens=st.integers(min_value=1, max_value=1000),
)
def test_scan_scope_preserves_its_thresholds(min_lines, min_tokens):
    scope = ScanScope((Path("."),), min_lines=min_lines, min_tokens=min_tokens)
    assert scope.min_lines == min_lines
    assert scope.min_tokens == min_tokens


@settings(max_examples=100, deadline=None)
@given(value=st.integers(max_value=0))
def test_scan_scope_refuses_non_positive_thresholds(value):
    with pytest.raises(EmptyScope):
        ScanScope((Path("."),), min_lines=value)
    with pytest.raises(EmptyScope):
        ScanScope((Path("."),), min_tokens=value)


@settings(max_examples=100, deadline=None)
@given(
    min_lines=st.integers(min_value=1, max_value=200),
    min_tokens=st.integers(min_value=1, max_value=1000),
)
def test_detector_command_carries_the_thresholds_and_paths(min_lines, min_tokens):
    scope = ScanScope((Path("."),), min_lines=min_lines, min_tokens=min_tokens)
    command = JscpdDetector(None, None)._command(scope, "/output")
    assert command[command.index("--min-lines") + 1] == str(min_lines)
    assert command[command.index("--min-tokens") + 1] == str(min_tokens)
    assert command[-1] == str(Path("."))


@settings(max_examples=100, deadline=None)
@given(pair=st.tuples(REGIONS, REGIONS))
def test_report_parser_round_trips_a_duplicate_pair(pair):
    (first_name, first_start, first_length), (second_name, second_start, second_length) = pair
    first = _region(first_name, first_start, first_length)
    second = _region(second_name, second_start, second_length)
    assume(first != second)
    raw = json.dumps(
        {
            "duplicates": [
                {
                    "firstFile": _json_region(first_name, first),
                    "secondFile": _json_region(second_name, second),
                }
            ]
        }
    )
    assert JscpdReportParser().parse(raw) == (Duplicate(first, second),)


@settings(max_examples=50, deadline=None)
@given(pairs=st.lists(st.tuples(REGIONS, REGIONS), max_size=4))
def test_report_parser_round_trips_every_pair(pairs):
    expected = []
    raw_duplicates = []
    for (n1, s1, l1), (n2, s2, l2) in pairs:
        first = _region(n1, s1, l1)
        second = _region(n2, s2, l2)
        if first == second:
            continue
        expected.append(Duplicate(first, second))
        raw_duplicates.append(
            {
                "firstFile": _json_region(n1, first),
                "secondFile": _json_region(n2, second),
            }
        )
    parsed = JscpdReportParser().parse(json.dumps({"duplicates": raw_duplicates}))
    assert parsed == tuple(expected)


@settings(max_examples=50, deadline=None)
@given(pairs=st.lists(st.tuples(REGIONS, REGIONS), max_size=4))
def test_writer_mentions_every_position_and_the_count(pairs):
    duplicates = []
    for (n1, s1, l1), (n2, s2, l2) in pairs:
        first = _region(n1, s1, l1)
        second = _region(n2, s2, l2)
        if first != second:
            duplicates.append(Duplicate(first, second))
    report = DuplicateReport(tuple(duplicates))
    stream = io.StringIO()
    ConsoleReportWriter(stream).write(report)
    output = stream.getvalue()
    if not duplicates:
        assert output == "No duplicate candidates found.\n"
        return
    for duplicate in duplicates:
        for region in (duplicate.first, duplicate.second):
            assert f"{region.path}:{region.start}-{region.end}" in output
    assert f"{len(duplicates)} duplicate candidate(s)." in output
