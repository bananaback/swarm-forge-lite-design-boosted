"""Hypothesis properties for crap4py's CRAP math, coverage, and ordering."""

import tempfile
from pathlib import Path

from crap4py.coverage import Coverage
from crap4py.function import Function
from crap4py.measurement import THRESHOLD, Measurement
from hypothesis import given, settings
from hypothesis import strategies as st

COMPLEXITIES = st.integers(min_value=1, max_value=50)
FRACTIONS = st.floats(
    min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False
)
LINE_HITS = st.dictionaries(
    st.integers(min_value=1, max_value=500),
    st.integers(min_value=0, max_value=20),
    min_size=1,
)


@settings(max_examples=100, deadline=None)
@given(complexity=COMPLEXITIES)
def test_crap_hits_the_coverage_endpoints(complexity):
    function = Function("fn", "module.py", 1, 2, complexity)
    assert function.crap(0.0) == complexity**2 + complexity
    assert function.crap(1.0) == complexity


@settings(max_examples=100, deadline=None)
@given(complexity=COMPLEXITIES, covered=FRACTIONS)
def test_crap_stays_between_complexity_and_zero_coverage(complexity, covered):
    function = Function("fn", "module.py", 1, 2, complexity)
    score = function.crap(covered)
    assert complexity - 1e-9 <= score <= complexity**2 + complexity + 1e-9


@settings(max_examples=100, deadline=None)
@given(complexity=COMPLEXITIES, first=FRACTIONS, second=FRACTIONS)
def test_crap_never_grows_with_coverage(complexity, first, second):
    function = Function("fn", "module.py", 1, 2, complexity)
    low, high = sorted((first, second))
    assert function.crap(low) >= function.crap(high) - 1e-9


@settings(max_examples=100, deadline=None)
@given(hits=LINE_HITS, complexity=COMPLEXITIES)
def test_measurement_follows_the_positive_line_fraction(hits, complexity):
    function = Function("fn", "module.py", min(hits), max(hits), complexity)
    measurement = Measurement(function, hits)
    positive = sum(1 for count in hits.values() if count > 0)
    expected = positive / len(hits)
    assert measurement.coverage_text() == f"{expected * 100:.1f}%"
    assert measurement.score_text() == f"{function.crap(expected):.1f}"
    assert measurement.exceeds() == (function.crap(expected) > THRESHOLD)


@settings(max_examples=100, deadline=None)
@given(hits=LINE_HITS, offset=st.integers(min_value=1, max_value=100))
def test_hits_outside_the_function_range_report_unmeasured(hits, offset):
    start = max(hits) + offset
    measurement = Measurement(Function("fn", "module.py", start, start + 1, 1), hits)
    assert measurement.coverage_text() == "unmeasured"
    assert measurement.score_text() == "unmeasured"
    assert measurement.sort_key()[0] is True


@settings(max_examples=100, deadline=None)
@given(first=COMPLEXITIES, second=COMPLEXITIES, hits=LINE_HITS)
def test_ranking_puts_the_worst_score_first(first, second, hits):
    start, end = min(hits), max(hits)
    left = Measurement(Function("a", "module.py", start, end, first), hits)
    right = Measurement(Function("b", "module.py", start, end, second), hits)
    ordered = sorted((left, right), key=Measurement.sort_key)
    assert ordered[0].sort_key()[1] <= ordered[1].sort_key()[1]


@settings(max_examples=25, deadline=None)
@given(hits=LINE_HITS)
def test_lcov_round_trips_line_hits(hits):
    with tempfile.TemporaryDirectory() as directory:
        module = Path(directory) / "module.py"
        module.write_text("x = 1\n")
        lcov = Path(directory) / "coverage.lcov"
        lines = [f"SF:{module}"]
        lines += [f"DA:{number},{count}" for number, count in sorted(hits.items())]
        lines.append("end_of_record")
        lcov.write_text("\n".join(lines) + "\n")
        function = Function("fn", str(module), min(hits), max(hits), 1)
        assert Coverage.load(lcov).hits_for(function) == hits
