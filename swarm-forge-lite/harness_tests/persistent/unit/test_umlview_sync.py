"""Unit tests for the umlview live-sync overlay (`sync_python.py`)."""

import sys
from pathlib import Path

PACK_ROOT = Path(__file__).resolve().parents[3]
UMLVIEW = PACK_ROOT / "tools" / "shared" / "umlview"
if str(UMLVIEW) not in sys.path:
    sys.path.insert(0, str(UMLVIEW))

import sync_python


def test_parse_crap_reads_measured_and_unmeasured_rows(tmp_path):
    report = tmp_path / "crap.txt"
    report.write_text(
        "CRAP Report\n"
        "===========\n"
        "Languages: python\n"
        "\n"
        "Function                     Namespace                  CC    Cov%     CRAP\n"
        "---------------------------------------------------------------------------\n"
        "of                           core.present.Present        2   87.5%      2.1\n"
        "adv                          mod.sub                    12     N/A      N/A\n"
    )

    rows = sync_python.parse_crap(report)

    assert rows[0] == {
        "name": "of",
        "namespace": "core.present.Present",
        "cc": 2,
        "coverage": 0.875,
        "crap": 2.1,
    }
    assert rows[1]["coverage"] is None and rows[1]["crap"] is None


def _model():
    return {
        "packages": [
            {
                "id": "core",
                "label": "Core",
                "classes": [
                    {
                        "id": "core.Present",
                        "name": "Present",
                        "annotations": {
                            "core": True,
                            "secret": "how a presence is held",
                        },
                        "ops": [
                            {
                                "name": "of",
                                "args": [{"name": "o"}],
                                "annotations": {"cqs": "query", "post": "a presence"},
                            },
                            {
                                "name": "gone",
                                "args": [],
                                "annotations": {"cqs": "command"},
                            },
                        ],
                    }
                ],
            }
        ]
    }


def _source(root):
    path = root / "core" / "present.py"
    path.parent.mkdir(parents=True)
    path.write_text(
        "class Present:\n"
        "    def of(self, observation: Observation) -> Present:\n"
        "        return self\n"
        "    def shows(self, subject: SubjectName) -> bool:\n"
        "        return True\n"
        "    def extra(self) -> int:\n"
        "        return 1\n"
    )


def test_overlay_replaces_signatures_and_flags_drift(tmp_path):
    _source(tmp_path)
    model = _model()

    counts = sync_python.overlay(model, sync_python.scan_source(tmp_path), {})

    assert counts == {
        "matched": 1,
        "missing": 0,
        "ambiguous": 0,
        "ops_updated": 1,
        "ops_new": 2,
        "ops_missing": 1,
        "ops_measured": 0,
    }
    cls = model["packages"][0]["classes"][0]
    assert cls["live"] == {"status": "synced", "source": "core/present.py"}
    assert cls["annotations"]["core"] is True and cls["annotations"]["secret"]
    assert "live" not in cls["annotations"]

    by_name = {op["name"]: op for op in cls["ops"]}
    assert by_name["of"]["args"] == [{"name": "observation", "type": "Observation"}]
    assert by_name["of"]["returns"] == "Present"
    assert by_name["of"]["annotations"]["cqs"] == "query"  # authored, kept
    assert by_name["of"]["annotations"]["post"] == "a presence"  # authored, kept
    assert by_name["of"]["live"] == {"status": "synced"}
    assert "def of" in by_name["of"]["code"] and "return self" in by_name["of"]["code"]
    assert by_name["shows"]["live"] == {"status": "new"}
    assert by_name["extra"]["live"] == {"status": "new"}
    assert by_name["gone"]["live"] == {"status": "missing"}


def test_overlay_attaches_metrics_by_class_and_method(tmp_path):
    _source(tmp_path)
    model = _model()
    rows = [
        {
            "name": "of",
            "namespace": "core.present.Present",
            "cc": 3,
            "coverage": 0.5,
            "crap": 6.25,
        },
    ]

    sync_python.overlay(model, sync_python.scan_source(tmp_path), {"of": rows})

    op = model["packages"][0]["classes"][0]["ops"][0]
    assert op["metrics"] == {"cc": 3, "coverage": 0.5, "crap": 6.25}


def test_overlay_matches_a_report_run_over_a_deeper_root(tmp_path):
    _source(tmp_path)
    model = _model()
    rows = [
        {
            "name": "of",
            "namespace": "app.pipeline.core.present.Present",
            "cc": 2,
            "coverage": 1.0,
            "crap": 2.0,
        },
    ]

    sync_python.overlay(model, sync_python.scan_source(tmp_path), {"of": rows})

    op = model["packages"][0]["classes"][0]["ops"][0]
    assert op["metrics"]["crap"] == 2.0


def test_overlay_flags_a_missing_class(tmp_path):
    _source(tmp_path)
    model = {
        "packages": [
            {
                "id": "core",
                "label": "Core",
                "classes": [
                    {"id": "core.Absent", "name": "Absent", "ops": []},
                ],
            }
        ]
    }

    counts = sync_python.overlay(model, sync_python.scan_source(tmp_path), {})

    assert counts["missing"] == 1
    assert model["packages"][0]["classes"][0]["live"] == {"status": "missing"}


def test_choose_class_disambiguates_by_id_segment(tmp_path):
    core = tmp_path / "core" / "refused.py"
    shell = tmp_path / "shell" / "refused.py"
    core.parent.mkdir(parents=True)
    shell.parent.mkdir(parents=True)
    core.write_text("class Refused:\n    pass\n")
    shell.write_text("class Refused:\n    pass\n")

    index = sync_python.scan_source(tmp_path)
    chosen = sync_python.choose_class(index["Refused"], {"id": "core.Refused"})

    assert chosen is not None and chosen["path"] == core.relative_to(tmp_path)
    assert sync_python.choose_class(index["Refused"], {"id": "other.Refused"}) is None
