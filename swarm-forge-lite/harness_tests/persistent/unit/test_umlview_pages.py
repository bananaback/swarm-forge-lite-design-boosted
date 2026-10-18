"""The checked-in umlview pages must be the current renderer's output.

`render.py` and `template.html` are the source of every page that the pack
ships: the two examples beside `render.py`, and the workplace diagrams under
`design/subsystems/*/`. A page that still carries the old template's `crapClass`
tier code, or that is not what the renderer writes today, is stale.

Every page is the render of the subsystem's `model.json`. The retired
`model.live.json` overlay no longer exists: `swarm.uml({op:'sync'})` updates
`model.json` itself, so there is one topology and one page.

The mutations this fails on: revert `template.html` to the tier-code version,
or edit a `model.json` and do not render its page again.
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

# The page loads these two libraries from the CDN. They are the only external
# references the template emits.
CDN_URLS = [
    "https://cdn.tailwindcss.com/3.4.16",
    "https://code.jquery.com/jquery-3.7.1.min.js",
]

DESIGN = PACK_ROOT / "design" / "subsystems"
EXAMPLES = [
    ("example.model.json", "example.model.html"),
    ("example.violation.model.json", "example.violation.model.html"),
]


def _subsystems():
    return sorted(DESIGN.iterdir()) if DESIGN.is_dir() else []


def _pairs():
    """Each (model, page) pair the pack ships: model.json -> model.html."""
    pairs = []
    for subsystem in _subsystems():
        page = subsystem / "model.html"
        model = subsystem / "model.json"
        if page.exists() and model.exists():
            pairs.append((model, page))
    for model_name, page_name in EXAMPLES:
        model, page = UMLVIEW / model_name, UMLVIEW / page_name
        if model.exists() and page.exists():
            pairs.append((model, page))
    return pairs


def _page_model(page):
    """The model JSON the page carries."""
    text = page.read_text()
    start = text.index("const MODEL = ") + len("const MODEL = ")
    end = text.index(";\nconst DIAGS", start)
    return json.loads(text[start:end].replace("<\\/", "</"))


def _live_fields(model):
    """The op counts of the live-only fields the page carries: (code, metrics)."""
    components = model.get("components") or model.get("packages") or []
    code = 0
    metrics = 0
    for component in components:
        for cls in component.get("classes", []):
            for op in cls.get("ops", []):
                code += "code" in op
                metrics += "metrics" in op
    return code, metrics


PAGES = _pairs()
IDS = [f"{page.parent.name}/{page.name}" for _model, page in PAGES]


def test_the_two_example_pages_are_covered():
    names = {page.name for _model, page in PAGES}

    assert {"example.model.html", "example.violation.model.html"} <= names
    assert len(PAGES) >= 2


def test_every_designed_subsystem_has_a_page():
    if not _subsystems() or not any((p / "model.json").exists() for p in _subsystems()):
        pytest.skip("no project design record in this pack")
    pages = {page.parent.name for _model, page in PAGES}
    designed = {
        p.name
        for p in _subsystems()
        if (p / "model.json").exists() and (p / "model.html").exists()
    }
    assert designed <= pages
    assert {"safety-rule-engine", "speaker-alerts"} <= designed


@pytest.mark.parametrize("model,page", PAGES, ids=IDS)
def test_the_page_equals_a_fresh_render(tmp_path, model, page):
    out = tmp_path / page.name
    render.render(model, out, render.DEFAULT_TEMPLATE, render.DEFAULT_DAGRE)

    assert out.read_text() == page.read_text()


@pytest.mark.parametrize("model,page", PAGES, ids=IDS)
def test_the_page_has_no_tier_code_and_only_the_two_pinned_cdn_urls(model, page):
    text = page.read_text()

    assert "crapClass" not in text
    assert re.findall(r'(?:src|href)="(https?://[^"]+)"', text) == CDN_URLS
