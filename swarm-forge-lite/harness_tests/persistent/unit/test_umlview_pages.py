"""The checked-in umlview example pages must be the current renderer's output.

`render.py` and `template.html` are the source of the two example pages beside
them. A page that still carries the old template's `crapClass` tier code, or that
is not what the renderer writes today, is stale.

The mutations this fails on: revert `template.html` to the tier-code version, or
edit an example `model.json` and do not render its page again.
"""

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

EXAMPLES = [
    ("example.model.json", "example.model.html"),
    ("example.violation.model.json", "example.violation.model.html"),
]


def _pairs():
    """Each (model, page) example pair the pack ships."""
    pairs = []
    for model_name, page_name in EXAMPLES:
        model, page = UMLVIEW / model_name, UMLVIEW / page_name
        if model.exists() and page.exists():
            pairs.append((model, page))
    return pairs


PAGES = _pairs()
IDS = [f"{page.parent.name}/{page.name}" for _model, page in PAGES]


def test_the_example_pages_are_covered():
    """Both shipped examples pair up, so the cases below cannot silently empty."""
    names = {page.name for _model, page in PAGES}

    assert {"example.model.html", "example.violation.model.html"} <= names


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
