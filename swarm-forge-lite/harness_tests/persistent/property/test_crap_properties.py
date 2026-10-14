"""Hypothesis properties for the pack's crapper report parsing."""

import swarm_json
from hypothesis import given, settings
from hypothesis import strategies as st

TOKEN = st.text(
    alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._",
    min_size=1,
    max_size=10,
)
COMPLEXITY = st.integers(min_value=1, max_value=200)
COVERAGE = st.one_of(
    st.just("N/A"),
    st.floats(
        min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False
    ).map(lambda value: f"{value:.1f}%"),
)
CRAP = st.one_of(
    st.just("N/A"),
    st.floats(min_value=0.0, max_value=1e6, allow_nan=False, allow_infinity=False).map(
        lambda value: f"{value:.1f}"
    ),
)
ROW = st.tuples(TOKEN, TOKEN, COMPLEXITY, COVERAGE, CRAP)


def _line(row) -> str:
    name, namespace, complexity, coverage, crap = row
    return f"{name:<30} {namespace:<35} {complexity:4d} {coverage:>7} {crap:>8}"


@settings(max_examples=100, deadline=None)
@given(rows=st.lists(ROW, max_size=8))
def test_every_printed_row_is_parsed_back(rows):
    text = "\n".join(_line(row) for row in rows) + "\n"
    parsed = swarm_json._crap_rows(text)
    assert [(row["function"], row["namespace"], row["cc"]) for row in parsed] == [
        (row[0], row[1], row[2]) for row in rows
    ]


@settings(max_examples=100, deadline=None)
@given(rows=st.lists(ROW, max_size=8))
def test_the_threshold_keeps_exactly_the_scores_above_it(rows):
    text = "\n".join(_line(row) for row in rows) + "\n"
    parsed = swarm_json._crap_rows(text)
    expected = [
        row
        for row in parsed
        if row["crap"] != "N/A" and float(row["crap"]) > swarm_json.CRAP_THRESHOLD
    ]
    assert swarm_json._crap_over(parsed) == expected
