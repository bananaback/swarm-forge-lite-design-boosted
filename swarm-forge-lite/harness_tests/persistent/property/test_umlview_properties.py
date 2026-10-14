"""Hypothesis properties for the ported CRAP grade (`render.py`).

The oracle: the grade is a clamped piecewise-linear map of the risk, so it can
never rise when the risk rises, and it always stays on the 1-10 scale.
"""

import sys
from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st

PACK_ROOT = Path(__file__).resolve().parents[3]
UMLVIEW = PACK_ROOT / "tools" / "shared" / "umlview"
if str(UMLVIEW) not in sys.path:
    sys.path.insert(0, str(UMLVIEW))

import render

RISK = st.floats(min_value=0.0, max_value=200.0, allow_nan=False, allow_infinity=False)


@settings(max_examples=100, deadline=None)
@given(RISK)
def test_the_grade_stays_on_the_1_to_10_scale(risk):
    assert render.GRADE_WORST <= render.crap_grade(risk) <= render.GRADE_BEST


@settings(max_examples=100, deadline=None)
@given(
    st.floats(min_value=0.0, max_value=200.0, allow_nan=False, allow_infinity=False),
    st.floats(min_value=0.0, max_value=200.0, allow_nan=False, allow_infinity=False),
)
def test_a_higher_risk_never_gives_a_higher_grade(first, second):
    low, high = min(first, second), max(first, second)

    assert render.crap_grade(low) >= render.crap_grade(high) - 1e-9


@settings(max_examples=100, deadline=None)
@given(RISK)
def test_a_missing_score_grades_worse_than_any_measured_score(risk):
    assert render.crap_grade(None) <= render.crap_grade(risk)
