"""A model class with no source class is not a measured module."""

import sys
from pathlib import Path

PACK_ROOT = Path(__file__).resolve().parents[3]
UMLVIEW = PACK_ROOT / "tools" / "shared" / "umlview"
if str(UMLVIEW) not in sys.path:
    sys.path.insert(0, str(UMLVIEW))

import render


def test_a_class_with_no_source_class_is_not_measured():
    cls = {
        "id": "payload.Payload",
        "live": {"status": "missing"},
        "ops": [{"name": "one"}, {"name": "two"}],
    }

    assert render.pool_crap([cls]) is None

    component = {"id": "payload", "classes": [cls]}
    render.stamp_grades([component])

    assert cls["crap"] is None
    assert cls.get("risk") is None
    assert "grade" not in cls
    assert "band" not in cls
    assert component["crap"] is None
    assert component.get("risk") is None
    assert "grade" not in component
    assert "band" not in component
