"""Unit tests for the umlview CRAP grade wrapper (`render.py`).

The cases mirror the upstream spec file
`spec/uml_viewer/domain/config_spec.clj` of unclebob/uml-viewer, so the port
stays checkable against the source it came from.

One deliberate deviation from upstream: a module with no functions contributes
no group at all. Upstream weights it as one function; that grades an enum (a
class with nothing to measure) red. The no-op case is separated from the
"has functions, has no metrics" case below.
"""

import json
import re
import sys
from pathlib import Path

import pytest

PACK_ROOT = Path(__file__).resolve().parents[3]
UMLVIEW = PACK_ROOT / "tools" / "shared" / "umlview"
if str(UMLVIEW) not in sys.path:
    sys.path.insert(0, str(UMLVIEW))

import render

# The real design model: the no-op classes in it are the case the rule protects.
_SAFETY_MODEL = (
    PACK_ROOT / "design" / "subsystems" / "safety-rule-engine" / "model.json"
)

# --------------------------------------------------------------------------- #
# crap-band and crap-risk
# --------------------------------------------------------------------------- #


def test_the_thresholds_are_green_8_yellow_12_red_20():
    assert render.CRAP_THRESHOLDS == {"green": 8, "yellow": 12, "red": 20}
    assert (render.GRADE_BEST, render.GRADE_MID, render.GRADE_WORST) == (10.0, 5.5, 1.0)


def test_a_missing_score_bands_red():
    assert render.crap_band(None) == "red"


def test_the_band_is_green_at_or_below_8():
    assert render.crap_band(0) == "green"
    assert render.crap_band(8) == "green"
    assert render.crap_band(8.1) == "yellow"


def test_the_band_is_yellow_through_12_and_red_beyond():
    assert render.crap_band(12) == "yellow"
    assert render.crap_band(12.1) == "red"
    assert render.crap_band(20) == "red"
    assert render.crap_band(100) == "red"


def test_crap_risk_is_mu_plus_sigma():
    assert render.crap_risk({"mu": 6, "sigma": 6}) == 12.0
    assert render.crap_risk({"mu": 6}) == 6.0


def test_crap_risk_is_none_without_a_mu():
    assert render.crap_risk({}) is None
    assert render.crap_risk(None) is None


# --------------------------------------------------------------------------- #
# crap-grade
# --------------------------------------------------------------------------- #


def test_the_grade_maps_8_to_10_12_to_5_5_and_20_to_1():
    assert render.crap_grade(8) == 10.0
    assert render.crap_grade(12) == 5.5
    assert render.crap_grade(20) == 1.0


def test_the_grade_clamps_outside_the_stops():
    assert render.crap_grade(0) == 10.0
    assert render.crap_grade(100) == 1.0


def test_the_grade_interpolates_between_the_stops():
    assert render.crap_grade(10) == 7.75
    assert render.crap_grade(16) == pytest.approx(3.25)


def test_the_grade_is_red_when_the_score_is_missing():
    assert render.crap_grade(None) == 1.0


def test_combined_grade_averages_the_present_grades():
    assert render.combined_grade(10.0, 10.0) == 10.0
    assert render.combined_grade(10.0, 1.0) == 5.5
    assert render.combined_grade(1.0, 1.0) == 1.0


def test_combined_grade_uses_the_one_present_grade():
    assert render.combined_grade(10.0, None) == 10.0
    assert render.combined_grade(None, 1.0) == 1.0
    assert render.combined_grade(None, None) is None


# --------------------------------------------------------------------------- #
# pool-crap
# --------------------------------------------------------------------------- #


def test_pool_crap_weights_each_function_once():
    modules = [
        {
            "ops": [
                {"metrics": {"crap": 2}},
                {"metrics": {"crap": 2}},
                {"metrics": {"crap": 2}},
            ]
        },
        {"ops": [{"metrics": {"crap": 20}}]},
    ]

    assert render.pool_crap(modules) == {"mu": 6.5, "max": 20.0, "sigma": 7.8, "n": 4}


def test_pool_crap_uses_the_n_of_a_summary_without_function_scores():
    modules = [
        {"crap": {"mu": 2, "sigma": 0, "max": 2, "n": 3}},
        {"crap": {"mu": 20, "sigma": 0, "max": 20, "n": 1}},
    ]

    assert render.pool_crap(modules) == {"mu": 6.5, "max": 20.0, "sigma": 7.8, "n": 4}


def test_a_module_without_crap_counts_as_red_once_per_function():
    modules = [
        {"crap": {"mu": 2, "sigma": 0, "max": 2, "n": 10}},
        {"ops": [{"name": "a"}, {"name": "b"}]},
    ]

    assert render.pool_crap(modules) == {"mu": 5.0, "max": 20.0, "sigma": 6.7, "n": 12}


def test_a_module_with_ops_and_no_metrics_counts_red_once_per_op():
    modules = [{"ops": [{"name": "a"}, {"name": "b"}, {"name": "c"}]}]

    assert render.pool_crap(modules) == {"mu": 20.0, "max": 20.0, "sigma": 0.0, "n": 3}


def test_a_module_with_no_ops_contributes_nothing():
    modules = [
        {"crap": {"mu": 2, "sigma": 0, "max": 2, "n": 1}},
        {},
    ]

    assert render.pool_crap(modules) == {"mu": 2.0, "max": 2.0, "sigma": 0.0, "n": 1}


def test_a_rolled_summary_wins_over_the_modules_own_ops():
    modules = [
        {
            "crap": {"mu": 2, "sigma": 0, "max": 2, "n": 10},
            "ops": [{"metrics": {"crap": 20}}],
        },
    ]

    assert render.pool_crap(modules, rolled=True) == {
        "mu": 2.0,
        "max": 2.0,
        "sigma": 0.0,
        "n": 10,
    }


def test_a_module_with_no_ops_and_no_crap_pools_to_nothing():
    assert render.pool_crap([{}]) is None


def test_a_no_op_class_leaves_its_package_pool_unchanged():
    """`contract.Verdict` and `contract.View` carry no functions. The real model
    pins the rule those classes protect: they never enter the package pool and
    they never grade the package red.

    The count is read from the model, not pinned: a class that gains or loses a
    function must move the pool, and only a class with no functions may not.
    """
    if not _SAFETY_MODEL.is_file():
        pytest.skip("no project safety model in this pack")
    raw = json.loads(_SAFETY_MODEL.read_text())
    doc, _errors = render.apply_policy(raw)
    components = render.display_components(doc)
    render.stamp_grades(components)
    contract = next(
        component for component in components if component["id"] == "contract"
    )

    no_ops = [cls for cls in contract["classes"] if not cls.get("ops")]
    counted = sum(len(cls.get("ops", [])) for cls in contract["classes"])
    assert no_ops, "the fixture must hold a class with no functions"
    assert contract["crap"]["n"] == counted
    assert contract["band"] in render.CRAP_THRESHOLDS


def test_pool_crap_skips_a_foreign_oval():
    assert render.pool_crap([{"shape": "oval"}]) is None
    assert render.pool_crap([]) is None


# --------------------------------------------------------------------------- #
# the emitted page
# --------------------------------------------------------------------------- #

CDN_URLS = [
    "https://cdn.tailwindcss.com/3.4.16",
    "https://code.jquery.com/jquery-3.7.1.min.js",
]


def _live_model():
    return {
        "title": "grade demo",
        "packages": [
            {
                "id": "core",
                "label": "Core",
                "classes": [
                    {
                        "id": "core.A",
                        "name": "A",
                        "ops": [
                            {
                                "name": "one",
                                "metrics": {"cc": 2, "coverage": 1.0, "crap": 2},
                            },
                            {
                                "name": "two",
                                "metrics": {"cc": 2, "coverage": 1.0, "crap": 2},
                            },
                            {
                                "name": "three",
                                "metrics": {"cc": 2, "coverage": 0.0, "crap": 20},
                            },
                        ],
                    }
                ],
            },
            {
                "id": "shell",
                "label": "Shell",
                "classes": [
                    {"id": "shell.B", "name": "B", "ops": [{"name": "unmeasured"}]}
                ],
            },
        ],
    }


def _render(tmp_path, model):
    model_path = tmp_path / "model.json"
    model_path.write_text(json.dumps(model))
    out_path = tmp_path / "model.html"
    code = render.render(
        model_path, out_path, render.DEFAULT_TEMPLATE, render.DEFAULT_DAGRE
    )
    text = out_path.read_text()
    start = text.index("const MODEL = ") + len("const MODEL = ")
    end = text.index(";\nconst DIAGS =", start)
    return code, text, json.loads(text[start:end].replace("<\\/", "</"))


def _module(emitted, component_id):
    return next(
        component
        for component in emitted["components"]
        if component["id"] == component_id
    )


def test_render_emits_the_pooled_crap_and_grade_per_class(tmp_path):
    _, _, emitted = _render(tmp_path, _live_model())
    cls = _module(emitted, "core")["classes"][0]

    assert cls["crap"] == {"mu": 8.0, "max": 20.0, "sigma": 8.5, "n": 3}
    assert cls["risk"] == pytest.approx(16.5)
    assert cls["grade"] == pytest.approx(2.96875)
    assert cls["band"] == "red"


def test_render_emits_the_class_grade_onto_its_package(tmp_path):
    _, _, emitted = _render(tmp_path, _live_model())

    assert _module(emitted, "core")["crap"] == {
        "mu": 8.0,
        "max": 20.0,
        "sigma": 8.5,
        "n": 3,
    }
    assert _module(emitted, "core")["grade"] == pytest.approx(2.96875)
    assert _module(emitted, "core")["band"] == "red"


def test_a_class_with_no_metrics_grades_one(tmp_path):
    _, _, emitted = _render(tmp_path, _live_model())
    cls = _module(emitted, "shell")["classes"][0]

    assert cls["crap"] == {"mu": 20.0, "max": 20.0, "sigma": 0.0, "n": 1}
    assert cls["grade"] == 1.0
    assert cls["band"] == "red"


def test_render_bands_each_op(tmp_path):
    _, _, emitted = _render(tmp_path, _live_model())
    ops = _module(emitted, "core")["classes"][0]["ops"]

    assert [op["band"] for op in ops] == ["green", "green", "red"]
    assert "band" not in _module(emitted, "shell")["classes"][0]["ops"][0]


def test_the_page_loads_exactly_the_two_pinned_cdn_urls(tmp_path):
    _, text, _ = _render(tmp_path, _live_model())

    assert re.findall(r'(?:src|href)="(https?://[^"]+)"', text) == CDN_URLS
