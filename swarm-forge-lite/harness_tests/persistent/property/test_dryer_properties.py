"""Hypothesis properties for the pack's dryer report parsing."""

import swarm_json
from hypothesis import given, settings
from hypothesis import strategies as st

NAME = st.text(alphabet="abcdefghijklmnopqrstuvwxyz/._", min_size=1, max_size=12)
LINE = st.integers(min_value=1, max_value=10_000)
SPAN = st.tuples(NAME, LINE, LINE)


def _position(row) -> str:
    name, start, end = row
    low, high = min(start, end), max(start, end)
    return f"/probe/{name}:{low}-{high}"


def _report(pairs) -> str:
    blocks = []
    for left, right in pairs:
        blocks.append(
            f"DUPLICATE score=0.90\n  {_position(left)}\n  {_position(right)}"
        )
    return "\n\n".join(blocks) + "\n"


@settings(max_examples=100, deadline=None)
@given(pairs=st.lists(st.tuples(SPAN, SPAN), max_size=6))
def test_every_printed_pair_is_parsed_back(pairs):
    expected = [[_position(left), _position(right)] for left, right in pairs]
    assert swarm_json._dry_pairs(_report(pairs)) == expected


@settings(max_examples=50, deadline=None)
@given(score=st.floats(min_value=0.0, max_value=1.0, allow_nan=False))
def test_a_report_without_positions_has_no_pairs(score):
    assert swarm_json._dry_pairs(f"DUPLICATE score={score:.2f}\n") == []


def test_a_clean_report_has_no_pairs():
    assert swarm_json._dry_pairs("No duplicate candidates found.\n") == []
