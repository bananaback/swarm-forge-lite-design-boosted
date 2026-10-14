"""Hypothesis properties for the umlmodel edit ops.

The oracle: an add followed by its reverse returns the model exactly, and a
set to the current value is a no-op.
"""

import copy
import json

from hypothesis import given, settings
from hypothesis import strategies as st
from umlmodel import mutate, validate

NAME = st.from_regex(r"[A-Za-z][A-Za-z0-9_]{0,6}", fullmatch=True)


def _base():
    return {
        "title": "demo",
        "direction": "tb",
        "levels": [["core"], ["shell"]],
        "packages": [
            {
                "id": "core",
                "label": "Core",
                "classes": [{"id": "core.A", "name": "A", "ops": []}],
            },
            {
                "id": "shell",
                "label": "Shell",
                "classes": [{"id": "shell.B", "name": "B", "ops": []}],
            },
        ],
        "edges": [{"from": "shell.B", "to": "core.A", "kind": "dependency"}],
    }


@settings(max_examples=60, deadline=None)
@given(
    name=NAME,
    kind=st.sampled_from(list(validate.KINDS)),
    core=st.booleans(),
)
def test_a_class_round_trips_through_add_and_remove(name, kind, core):
    model = _base()
    cid = f"core.P{name}"
    mutate.add_class(model, {"id": cid, "package": "core", "core": core})
    mutate.add_edge(model, {"from": "shell.B", "to": cid, "kind": kind})
    assert validate.errors(model) == []

    mutate.remove_edge(model, {"from": "shell.B", "to": cid})
    mutate.remove_class(model, {"id": cid})
    assert model == _base()


@settings(max_examples=60, deadline=None)
@given(title=st.text(min_size=1, max_size=20))
def test_setting_the_title_to_the_current_value_is_a_no_op(title):
    model = _base()
    model["title"] = title
    before = copy.deepcopy(model)

    mutate.set_title(model, {"title": title})

    assert model == before


@settings(max_examples=60, deadline=None)
@given(value=st.sampled_from(["true", "false", "7", "null", "3.5"]))
def test_set_annotation_decodes_a_json_value(value):
    model = _base()
    mutate.set_annotation(model, {"id": "core.A", "key": "k", "value": value})
    stored = model["packages"][0]["classes"][0]["annotations"]["k"]
    assert stored == json.loads(value)
