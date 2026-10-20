"""Behavior tests for the design surface. Run: python3 -m pytest -q tools/design."""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import arch  # noqa: E402
import class_model  # noqa: E402
import overlay  # noqa: E402

SAMPLE = {
    "core/port.py": """
from typing import Protocol

class Port(Protocol):
    def deliver(self, item: str) -> bool: ...
""",
    "shell/transport.py": """
class MessagePort:
    def deliver(self, item: str) -> bool:
        return True
""",
    "core/whole.py": """
from shell.part import Part

class Whole:
    def __init__(self, part: Part) -> None:
        self.part = part

class Built:
    def __init__(self) -> None:
        self.part = Part()
""",
    "shell/part.py": "class Part:\n    pass\n",
}


def _sample_tree(tmp_path: Path) -> Path:
    for name, body in SAMPLE.items():
        path = tmp_path / "pkg" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
    (tmp_path / "pkg" / "__init__.py").write_text("", encoding="utf-8")
    return tmp_path


def test_scan_reads_stereotypes(tmp_path):
    classes = class_model.scan(_sample_tree(tmp_path), ("pkg",))
    assert classes["Port"].stereotype == "interface"
    assert classes["MessagePort"].stereotype == "concrete"
    assert classes["MessagePort"].methods == ["deliver"]


def test_structural_protocol_is_inferred(tmp_path):
    classes = class_model.scan(_sample_tree(tmp_path), ("pkg",))
    edges = class_model.relations(classes)
    assert ("MessagePort", "Port", "implements") in edges


def test_aggregation_vs_composition(tmp_path):
    classes = class_model.scan(_sample_tree(tmp_path), ("pkg",))
    edges = class_model.relations(classes)
    assert ("Whole", "Part", "aggregation") in edges
    assert ("Built", "Part", "composition") in edges


def test_overlay_add_diff_and_remove():
    data = {"nodes": [], "edges": [], "annotations": {}}
    overlay.add_node(data, {"id": "pkg.core.Port2", "subsystem": "pkg",
                            "stereotype": "interface", "layer": "core",
                            "since": "2026-01-01", "reason": "test"})
    rows = overlay.diff(set(), set(), data)
    assert any("design-only: pkg.core.Port2" in row for row in rows)

    overlay.add_edge(data, {"from": "pkg.core.Port2", "to": "pkg.core.Port",
                            "kind": "implements", "since": overlay.today()})
    problems = overlay.validate(data, set(), set())
    assert any("unknown node pkg.core.Port" in p for p in problems)

    overlay.remove_node(data, "pkg.core.Port2")
    assert data["nodes"] == [] and data["edges"] == []


def test_overlay_marks_a_node_stale_once_code_has_it():
    data = {"nodes": [{"id": "pkg.core.Port", "subsystem": "pkg", "stereotype": "interface",
                       "layer": "core", "since": "2026-01-01"}], "edges": [], "annotations": {}}
    rows = overlay.diff({"pkg.core.Port"}, set(), data)
    assert any(row.startswith("stale overlay: pkg.core.Port") for row in rows)


def test_runtime_validation_names_missing_box(tmp_path):
    pipeline = tmp_path / "pipeline"
    (pipeline / "detector").mkdir(parents=True)
    data = {"zones": [], "nodes": [{"id": "detector", "package": "detector"}], "edges": []}
    assert arch.runtime_problems(data, pipeline) == []
    data["nodes"] = []
    problems = arch.runtime_problems(data, pipeline)
    assert any("detector" in p for p in problems)


def test_runtime_validation_rejects_dangling_edge(tmp_path):
    pipeline = tmp_path / "pipeline"
    (pipeline / "detector").mkdir(parents=True)
    data = {"zones": [], "nodes": [{"id": "detector", "package": "detector"}],
            "edges": [{"from": "detector", "to": "ghost", "kind": "solid"}]}
    assert any("ghost" in p for p in arch.runtime_problems(data, pipeline))


def test_cli_validates_the_real_project():
    assert arch.main(["classes", "validate"]) == 0
    assert arch.main(["runtime", "validate"]) == 0
