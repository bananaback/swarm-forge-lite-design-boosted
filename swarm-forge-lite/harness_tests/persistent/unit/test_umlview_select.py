"""Selection drives the canvas focus and the panel.

A click on a class box, a click on an entity row, the back link, and a click on
empty canvas each change two things: the view transform and the panel. The page
builds its SVG and its handlers at runtime, so this test runs the page under
node (`umlview_interaction_driver.js`) and asserts the state change of each
path. Without node the test skips.

The mutations this fails on: drop `select`/`deselect` from the template, leave
the canvas click on the old `detail(id)` only, or stop the generic entity list
from coming back on a deselect.
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

PACK_ROOT = Path(__file__).resolve().parents[3]
UMLVIEW = PACK_ROOT / "tools" / "shared" / "umlview"
if str(UMLVIEW) not in sys.path:
    sys.path.insert(0, str(UMLVIEW))

import render

DRIVER = (
    Path(__file__).resolve().parent.parent / "support" / "umlview_interaction_driver.js"
)

NODE = shutil.which("node")
pytestmark = pytest.mark.skipif(NODE is None, reason="node is not installed")

CANVAS_PICK = "core.alpha"
ROW_PICK = "shell.gamma"
NOOP_PICK = "core.beta"


def _select_model():
    """Three entities: one for a canvas click, one for an entity row, one
    without a method. Each carries a description and a method body."""
    return {
        "title": "select demo",
        "packages": [
            {
                "id": "core",
                "label": "Core",
                "classes": [
                    {
                        "id": "core.Alpha",
                        "name": "Alpha",
                        "annotations": {
                            "core": True,
                            "responsibility": "Count the things.",
                        },
                        "ops": [
                            {
                                "name": "count",
                                "returns": "int",
                                "code": "def count(self):\n    return 1\n",
                                "annotations": {"cqs": "query"},
                                "metrics": {"cc": 1, "coverage": 1.0, "crap": 1.0},
                            }
                        ],
                    },
                    {
                        "id": "core.Beta",
                        "name": "Beta",
                        "annotations": {"secret": "the beta bytes"},
                    },
                ],
            },
            {
                "id": "shell",
                "label": "Shell",
                "classes": [
                    {
                        "id": "shell.Gamma",
                        "name": "Gamma",
                        "annotations": {
                            "core": False,
                            "responsibility": "Run the thing.",
                        },
                        "ops": [
                            {
                                "name": "run",
                                "code": "def run(self):\n    pass\n",
                                "metrics": {"cc": 1, "coverage": 1.0, "crap": 1.0},
                            }
                        ],
                    }
                ],
            },
        ],
    }


@pytest.fixture(scope="module")
def state(tmp_path_factory):
    root = tmp_path_factory.mktemp("select")
    model_path = root / "model.json"
    model_path.write_text(json.dumps(_select_model()))
    out_path = root / "model.html"
    render.render(model_path, out_path, render.DEFAULT_TEMPLATE, render.DEFAULT_DAGRE)
    proc = subprocess.run(
        [NODE, str(DRIVER), str(out_path), CANVAS_PICK, ROW_PICK, NOOP_PICK],
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(proc.stdout)


def _step(state, label):
    return next(step for step in state["steps"] if step["label"] == label)


def _box(state, cid):
    return next(box for box in state["classes"] if box["id"] == cid)


def _screen_center(state, step, cid):
    box = _box(state, cid)
    return (
        step["view"]["x"] + box["cx"] * step["view"]["k"],
        step["view"]["y"] + box["cy"] * step["view"]["k"],
    )


def _assert_centered(state, label, cid):
    step = _step(state, label)
    x, y = _screen_center(state, step, cid)

    assert x == pytest.approx(state["rect"]["width"] / 2, abs=1)
    assert y == pytest.approx(state["rect"]["height"] / 2, abs=1)


def test_the_page_exposes_select_deselect_and_the_view(state):
    assert state["api"] == ["deselect", "select", "view"]


def test_select_shows_the_entity_detail(state):
    panel = _step(state, "select:api")["panel"]

    assert "Alpha" in panel
    assert 'class="code' in panel


def test_select_focuses_the_entity_box(state):
    assert _step(state, "select:api")["transform"] != _step(state, "load")["transform"]
    _assert_centered(state, "select:api", CANVAS_PICK)


def test_select_highlights_the_entity_and_dims_the_rest(state):
    step = _step(state, "select:api")

    assert step["lit"] == [CANVAS_PICK]
    assert "core.beta" in step["dimmed"]


def test_deselect_restores_the_entity_list(state):
    step = _step(state, "deselect:api")

    assert "All entities" in step["panel"]
    assert "Alpha" in step["panel"]
    assert "Count the things." in step["panel"]
    assert "Methods" not in step["panel"]
    assert step["lit"] == []
    assert step["dimmed"] == []
    assert step["tipHidden"] is True


def test_a_canvas_click_on_a_class_selects_it(state):
    step = _step(state, "canvas:cls")

    assert "Alpha" in step["panel"]
    assert 'class="code' in step["panel"]
    _assert_centered(state, "canvas:cls", CANVAS_PICK)


def test_a_click_on_empty_canvas_deselects(state):
    panel = _step(state, "canvas:empty")["panel"]

    assert "All entities" in panel
    assert "Methods" not in panel


def test_an_entity_row_click_selects_that_entity(state):
    step = _step(state, "list:row")

    assert "Gamma" in step["panel"]
    assert 'class="code' in step["panel"]
    _assert_centered(state, "list:row", ROW_PICK)


def test_the_back_link_returns_to_the_entity_list(state):
    panel = _step(state, "detail:back")["panel"]

    assert "All entities" in panel
    assert "Methods" not in panel


def test_a_class_with_no_functions_says_there_is_nothing_to_measure(state):
    panel = _step(state, "select:noop")["panel"]

    assert "nothing to measure" in panel
    assert "grade" not in panel
