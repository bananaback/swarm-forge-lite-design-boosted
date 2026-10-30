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


FAKE = {
    "rule_check_osd/legend.py": """
class ClassPair:
    def of(self, left, right):
        return self

class ClassLegend:
    def of(self, pair: ClassPair) -> None:
        self.pair = pair

    def empty(self):
        return ClassLegend()
""",
    "rule_check_osd/shell/overlay.py": """
class DebugOverlay:
    def on_frame(self, frame) -> None:
        legend = ClassLegend.empty()
        self.legend = legend
""",
    "rule_check_osd/shell/draw.py": """
class OsdDraw:
    def draw(self) -> None:
        print(ClassLegend.empty())
""",
    "rule_check_osd/shell/hud.py": """
class Hud:
    def paint(self) -> None:
        overlay = DebugOverlay()
        self.overlay = overlay
""",
}


def _fake_project(tmp_path: Path, monkeypatch) -> None:
    for name, body in FAKE.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
    monkeypatch.setattr(arch, "PIPELINE", tmp_path)
    monkeypatch.setattr(arch.paths, "DESIGN", tmp_path / "design.json")


def _printed_names(output: str) -> list[str]:
    names = []
    for line in output.splitlines():
        if not line.strip() or line.startswith("("):
            continue
        names.append(line.split()[0])
    return names


def _incoming_names(output: str) -> list[str]:
    names = []
    for line in output.splitlines():
        if "in:" in line:
            names.append(line.split("in:", 1)[1].split("(")[0].strip())
    return names


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
    assert arch.main(["docs", "validate"]) == 0


def test_classes_deps_names_the_classes_that_depend_on_it(tmp_path, monkeypatch, capsys):
    _fake_project(tmp_path, monkeypatch)
    assert arch.main(["classes", "deps", "rule_check_osd.legend.ClassLegend"]) == 0
    names = _printed_names(capsys.readouterr().out)
    assert sorted(names) == ["DebugOverlay", "OsdDraw"]


def test_classes_deps_accepts_a_unique_class_name(tmp_path, monkeypatch, capsys):
    _fake_project(tmp_path, monkeypatch)
    assert arch.main(["classes", "deps", "ClassLegend"]) == 0
    names = _printed_names(capsys.readouterr().out)
    assert sorted(names) == ["DebugOverlay", "OsdDraw"]


def test_classes_deps_transitive_names_the_indirect_dependents(tmp_path, monkeypatch, capsys):
    _fake_project(tmp_path, monkeypatch)
    assert arch.main(["classes", "deps", "rule_check_osd.legend.ClassLegend", "--transitive"]) == 0
    names = _printed_names(capsys.readouterr().out)
    assert sorted(names) == ["DebugOverlay", "Hud", "OsdDraw"]


def test_classes_deps_rejects_an_ambiguous_class_name(tmp_path, monkeypatch, capsys):
    _fake_project(tmp_path, monkeypatch)
    duplicate = tmp_path / "detector" / "legend.py"
    duplicate.parent.mkdir(parents=True, exist_ok=True)
    duplicate.write_text("class ClassLegend:\n    pass\n", encoding="utf-8")
    assert arch.main(["classes", "deps", "ClassLegend"]) == 1
    assert "ambiguous" in capsys.readouterr().err


def test_classes_deps_agrees_with_classes_show_on_the_real_project(capsys):
    assert arch.main(["classes", "show", "rule_check_osd.legend.ClassLegend"]) == 0
    dependents = _incoming_names(capsys.readouterr().out)
    assert dependents
    assert arch.main(["classes", "deps", "rule_check_osd.legend.ClassLegend"]) == 0
    named = _printed_names(capsys.readouterr().out)
    assert set(dependents) <= set(named)


EDGE_FROM = "rule_check_osd.legend.ClassLegend"
EDGE_TO = "rule_check_osd.shell.draw.OsdDraw"


def _design(tmp_path: Path) -> dict:
    return json.loads((tmp_path / "design.json").read_text(encoding="utf-8"))


def test_classes_add_edge_accepts_from_and_to_flags(tmp_path, monkeypatch, capsys):
    _fake_project(tmp_path, monkeypatch)
    assert arch.main([
        "classes", "add", "edge", "--from", EDGE_FROM, "--to", EDGE_TO,
    ]) == 0
    edge = _design(tmp_path)["edges"][0]
    assert (edge["from"], edge["to"]) == (EDGE_FROM, EDGE_TO)
    assert edge["id"] == f"{EDGE_FROM}->{EDGE_TO}"
    assert f"edge {EDGE_FROM}->{EDGE_TO}" in capsys.readouterr().out


def test_classes_add_edge_derives_the_id_from_two_positionals(tmp_path, monkeypatch):
    _fake_project(tmp_path, monkeypatch)
    assert arch.main(["classes", "add", "edge", EDGE_FROM, EDGE_TO]) == 0
    edge = _design(tmp_path)["edges"][0]
    assert (edge["from"], edge["to"]) == (EDGE_FROM, EDGE_TO)
    assert edge["id"] == f"{EDGE_FROM}->{EDGE_TO}"


def test_classes_add_edge_keeps_the_legacy_id_form(tmp_path, monkeypatch):
    _fake_project(tmp_path, monkeypatch)
    assert arch.main([
        "classes", "add", "edge", "legacy-edge", EDGE_FROM, EDGE_TO,
    ]) == 0
    edge = _design(tmp_path)["edges"][0]
    assert (edge["from"], edge["to"]) == (EDGE_FROM, EDGE_TO)
    assert edge["id"] == "legacy-edge"


def test_classes_add_edge_rejects_a_lone_from_flag(tmp_path, monkeypatch, capsys):
    _fake_project(tmp_path, monkeypatch)
    assert arch.main(["classes", "add", "edge", "--from", EDGE_FROM]) == 1
    assert "both --from and --to" in capsys.readouterr().err


def test_classes_add_node_honours_the_layer_it_was_given(tmp_path, monkeypatch, capsys):
    _fake_project(tmp_path, monkeypatch)
    node_id = "rule_check_osd.core.proposed.ProposedCheck"
    assert arch.main([
        "classes", "add", "node", node_id,
        "--subsystem", "rule_check_osd",
        "--module", "rule_check_osd/core/proposed",
        "--layer", "shell",
    ]) == 0
    assert _design(tmp_path)["nodes"][0]["layer"] == "shell"

    assert arch.main([
        "classes", "ls", "--subsystem", "rule_check_osd", "--layer", "shell",
    ]) == 0
    assert node_id in _printed_names(capsys.readouterr().out)

    assert arch.main([
        "classes", "ls", "--subsystem", "rule_check_osd", "--layer", "core",
    ]) == 0
    assert node_id not in _printed_names(capsys.readouterr().out)

    assert arch.main(["classes", "show", node_id]) == 0
    assert " shell " in capsys.readouterr().out


def _spec_with_classes(tmp_path: Path, rows: str) -> Path:
    spec = f"""# fake

## Responsibility
x

## Structure
x

## Classes
| Class | What it does |
|---|---|
{rows}

## Flow
x

## Design rules
x

## Rejected
x
"""
    path = tmp_path / "fake.md"
    path.write_text(spec, encoding="utf-8")
    return tmp_path


def _subsystem_model():
    info = class_model.ClassInfo(name="RealOne", module="sub/core/real", group="core")
    return {"sub.core.real.RealOne": ("sub", info)}


def test_docs_validate_reports_a_class_that_does_not_exist(tmp_path, monkeypatch):
    monkeypatch.setattr(arch, "SPECS", {"fake.md": "sub"})
    spec_dir = _spec_with_classes(
        tmp_path,
        "| `RealOne` | exists |\n| `GhostClass` | no such class |",
    )
    problems = arch.docs_problems(spec_dir, _subsystem_model())
    assert any(
        "fake.md: names a class that does not exist: GhostClass" in problem
        for problem in problems
    )


def test_docs_validate_cli_exits_1_for_a_missing_class(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(arch, "SPECS", {"fake.md": "sub"})
    monkeypatch.setattr(arch, "SPEC_DIR", tmp_path)
    _spec_with_classes(tmp_path, "| `GhostClass` | no such class |")
    assert arch.main(["docs", "validate"]) == 1
    out = capsys.readouterr().out
    assert "violation: fake.md: names a class that does not exist: GhostClass" in out


def test_docs_validate_cli_accepts_a_class_declared_in_the_overlay(
    tmp_path, monkeypatch, capsys
):
    monkeypatch.setattr(arch, "SPECS", {"fake.md": "sub"})
    monkeypatch.setattr(arch, "SPEC_DIR", tmp_path)
    _spec_with_classes(tmp_path, "| `GhostClass` | declared in the overlay |")
    design = tmp_path / "design.json"
    design.write_text(
        json.dumps({
            "nodes": [{"id": "sub.core.ghost.GhostClass", "subsystem": "sub",
                       "stereotype": "class", "layer": "core"}],
            "edges": [],
            "annotations": {},
        }),
        encoding="utf-8",
    )
    monkeypatch.setattr(arch.paths, "DESIGN", design)
    assert arch.main(["docs", "validate"]) == 0
    assert "ok: 1 specs" in capsys.readouterr().out


def test_docs_validate_accepts_a_class_declared_in_the_overlay(tmp_path, monkeypatch):
    monkeypatch.setattr(arch, "SPECS", {"fake.md": "sub"})
    spec_dir = _spec_with_classes(
        tmp_path,
        "| `RealOne` | exists |\n| `GhostClass` | declared in the overlay |",
    )
    problems = arch.docs_problems(
        spec_dir, _subsystem_model(), declared={"GhostClass"}
    )
    assert not any("GhostClass" in problem for problem in problems)


def test_docs_validate_ignores_constants_in_a_classes_table(tmp_path, monkeypatch):
    monkeypatch.setattr(arch, "SPECS", {"fake.md": "sub"})
    spec_dir = _spec_with_classes(
        tmp_path,
        "| `RealOne` | exists |\n| `MQTT_ALERT_TOPIC` | a constant, not a class |",
    )
    problems = arch.docs_problems(spec_dir, _subsystem_model())
    assert not any("MQTT_ALERT_TOPIC" in problem for problem in problems)
