"""The class box: its rows, its text, and its layout.

The template builds each class box with inline SVG: a header (note, name,
core/shell tag), a divider, one line per field or op (an op line may carry a
right-anchored CRAP label), and the pooled class grade. The grade used to hang
on the last row's baseline, one pixel above the last op's CRAP label. The fix
gives the grade a footer band of its own.

A field row draws a member of one of three shapes: a plain string, `{text}`
(the live source line), or `{name, type}` (an authored record). The row used to
read `field.name` only, so every text-shaped field drew `+ undefined`.

The boxes are produced at runtime by the template's own `draw()` (dagre is
embedded in the page), so this test runs the page under node and parses the SVG
it emits. Without node the test skips: it is a rendering test, not a unit of
pure Python logic.

The defects this fails on: revert `template.html` to draw the grade at
`y + box.h - 6` with the box height `30 + rows * 16 + 8`, or to build a field
row from `field.name` alone.
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

DRIVER = Path(__file__).resolve().parent.parent / "support" / "umlview_svg_driver.js"

NODE = shutil.which("node")
pytestmark = pytest.mark.skipif(NODE is None, reason="node is not installed")

CHAR_W = 0.6  # an SVG glyph's width as a fraction of its em size

SAFETY_PAGE = PACK_ROOT / "design" / "subsystems" / "safety-rule-engine" / "model.html"


def _svg_boxes(page_path):
    proc = subprocess.run(
        [NODE, str(DRIVER), str(page_path)],
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(proc.stdout)["classes"]


def _rendered_boxes(tmp_path, model):
    model_path = tmp_path / "model.json"
    model_path.write_text(json.dumps(model))
    out_path = tmp_path / "model.html"
    render.render(model_path, out_path, render.DEFAULT_TEMPLATE, render.DEFAULT_DAGRE)
    return _svg_boxes(out_path)


def _x_range(text):
    width = len(text["text"]) * text["font"] * CHAR_W
    if text["anchor"] == "end":
        return (text["x"] - width, text["x"])
    if text["anchor"] == "middle":
        return (text["x"] - width / 2, text["x"] + width / 2)
    return (text["x"], text["x"] + width)


def _collisions(texts):
    found = []
    for i in range(len(texts)):
        for j in range(i + 1, len(texts)):
            first, second = texts[i], texts[j]
            left = max(_x_range(first)[0], _x_range(second)[0])
            right = min(_x_range(first)[1], _x_range(second)[1])
            if right > left and abs(first["y"] - second["y"]) < min(
                first["font"], second["font"]
            ):
                found.append((first, second))
    return found


def _assert_clean_boxes(classes):
    for box in classes:
        bad = _collisions(box["texts"])
        assert not bad, f"{box['id']} collides: " + "; ".join(
            f"{first['text']!r}@y{first['y']:.0f} vs {second['text']!r}@y{second['y']:.0f}"
            for first, second in bad
        )


def _grade_model():
    """A pooled grade everywhere it can appear: with rows, with no rows, and
    without a pooled grade (the foreign oval)."""
    return {
        "title": "grade overlap demo",
        "packages": [
            {
                "id": "core",
                "label": "Core",
                "classes": [
                    {
                        "id": "core.Worker",
                        "name": "Worker",
                        "ops": [
                            {
                                "name": "measure",
                                "metrics": {"cc": 4, "coverage": 1.0, "crap": 4.0},
                            },
                            {
                                "name": "__init__",
                                "args": [{"name": "state", "type": "State"}],
                                "returns": "None",
                                "metrics": {"cc": 1, "coverage": 1.0, "crap": 1.0},
                            },
                        ],
                    },
                    {"id": "core.Empty", "name": "Empty"},
                    {
                        "id": "core.Labels",
                        "name": "Labels",
                        "stereotype": "enum",
                        "fields": [{"name": "YES"}, {"name": "NO"}],
                    },
                ],
            }
        ],
        "foreign": [
            {
                "id": "ext.Thing",
                "name": "Thing",
                "shape": "oval",
                "ops": [
                    {"name": "poke", "metrics": {"cc": 2, "coverage": 1.0, "crap": 2.0}}
                ],
            }
        ],
    }


def test_the_class_grade_clears_the_last_row(tmp_path):
    """The pooled grade must clear the last op row and its CRAP label."""
    classes = _rendered_boxes(tmp_path, _grade_model())
    worker = next(box for box in classes if box["id"] == "core.worker")

    _assert_clean_boxes([worker])


def test_a_class_with_no_pooled_grade_stays_sound(tmp_path):
    """A class without a pooled grade keeps its rows and draws no grade."""
    classes = _rendered_boxes(tmp_path, _grade_model())
    oval = next(box for box in classes if box["id"] == "ext.thing")

    assert all("CRAP" not in text["text"] for text in oval["texts"])
    _assert_clean_boxes([oval])


def test_a_class_with_no_rows_stays_sound(tmp_path):
    """A class with no rows keeps its header clear of everything else."""
    classes = _rendered_boxes(tmp_path, _grade_model())
    empty = next(box for box in classes if box["id"] == "core.empty")

    _assert_clean_boxes([empty])


def test_a_class_with_no_functions_draws_no_grade(tmp_path):
    """A class with nothing to measure carries no pooled grade on its box."""
    classes = _rendered_boxes(tmp_path, _grade_model())
    labels = next(box for box in classes if box["id"] == "core.labels")

    assert any("YES" in text["text"] for text in labels["texts"])
    assert all("CRAP" not in text["text"] for text in labels["texts"])


def _field_model():
    """One field of each accepted shape: a text line, a name and type, and a
    plain string."""
    return {
        "title": "field shapes",
        "packages": [
            {
                "id": "core",
                "label": "Core",
                "classes": [
                    {
                        "id": "core.Shapes",
                        "name": "Shapes",
                        "fields": [
                            {"text": "YES"},
                            {"name": "isbn", "type": "String"},
                            "plain",
                        ],
                    }
                ],
            }
        ],
    }


def test_a_field_row_reads_every_member_shape(tmp_path):
    """A field row draws the text, or name: type, or the plain string."""
    classes = _rendered_boxes(tmp_path, _field_model())
    shapes = next(box for box in classes if box["id"] == "core.shapes")
    rows = [text["text"] for text in shapes["texts"]]

    assert "+ YES" in rows
    assert "+ isbn: String" in rows
    assert "+ plain" in rows


def test_a_field_row_never_draws_undefined(tmp_path):
    """No text-shaped field leaks the missing `name` into the box."""
    classes = _rendered_boxes(tmp_path, _field_model())

    assert [
        text["text"]
        for box in classes
        for text in box["texts"]
        if "undefined" in text["text"]
    ] == []


def test_the_checked_in_safety_page_draws_no_undefined():
    """The real page: the live overlay writes every field as `{text}`."""
    if not SAFETY_PAGE.is_file():
        pytest.skip("no project safety page in this pack")
    boxes = _svg_boxes(SAFETY_PAGE)

    assert [
        text["text"]
        for box in boxes
        for text in box["texts"]
        if "undefined" in text["text"]
    ] == []
