"""Behavior tests for the design surface (rules 6–20).

They import the tools in-process, so they need a parseable pack config; without
one the module skips rather than failing a bare clone.
"""

from __future__ import annotations

import json
import sys

import pytest
from pathlib import Path

PACK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PACK / "tools" / "design"))

try:
    import arch  # noqa: E402
except SystemExit as error:  # no pack config yet
    pytest.skip(f"design surface needs a pack config: {error}", allow_module_level=True)

import class_model  # noqa: E402
import overlay  # noqa: E402
import runtime_view  # noqa: E402

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


def test_layer_violations_apply_the_dependency_rule_to_every_edge_kind():
    core = class_model.ClassInfo(name="Rules", module="safety/rules", group="safety")
    guard = class_model.ClassInfo(name="Guard", module="safety/guard", group="safety")
    shell = class_model.ClassInfo(
        name="Speaker", module="safety/shell/speaker", group="shell"
    )
    classes = {"Rules": core, "Guard": guard, "Speaker": shell}

    for kind in ("dependency", "composition", "aggregation", "extends", "implements"):
        assert arch.layer_violations(classes, [("Rules", "Speaker", kind)]) == [
            f"core depends on shell: Rules -> Speaker ({kind})"
        ]

    assert arch.layer_violations(classes, [("Speaker", "Rules", "composition")]) == []
    assert arch.layer_violations(classes, [("Rules", "Guard", "dependency")]) == []
    assert arch.layer_violations(classes, [("Rules", "Ghost", "dependency")]) == []


def test_classes_diff_reports_annotations_instead_of_an_empty_overlay(
    tmp_path, monkeypatch, capsys
):
    _fake_project(tmp_path, monkeypatch)
    (tmp_path / "design.json").write_text(
        json.dumps(
            {
                "nodes": [],
                "edges": [],
                "annotations": {"rule_check_osd.legend.ClassLegend": {"note": "why"}},
            }
        ),
        encoding="utf-8",
    )

    assert arch.main(["classes", "diff"]) == 0
    output = capsys.readouterr().out
    assert "overlay empty" not in output
    assert "1 annotations" in output


def test_classes_diff_flags_an_annotation_with_no_class(tmp_path, monkeypatch, capsys):
    _fake_project(tmp_path, monkeypatch)
    (tmp_path / "design.json").write_text(
        json.dumps(
            {
                "nodes": [],
                "edges": [],
                "annotations": {"rule_check_osd.legend.Gone": {"note": "why"}},
            }
        ),
        encoding="utf-8",
    )

    assert arch.main(["classes", "diff"]) == 0
    assert "stale overlay annotation" in capsys.readouterr().out
    assert arch.main(["classes", "diff", "--strict"]) == 1


def test_runtime_render_uses_the_authored_title(tmp_path):
    model = {
        "title": "Control server — runtime architecture",
        "canvas": [100, 100],
        "zones": [],
        "nodes": [
            {
                "id": "main",
                "x": 10,
                "y": 10,
                "w": 100,
                "h": 40,
                "label": "app.main",
                "sub": "wire",
                "note": None,
                "tone": "entry",
            }
        ],
        "edges": [],
    }
    source = tmp_path / "runtime.json"
    source.write_text(json.dumps(model), encoding="utf-8")
    out = tmp_path / "architecture.html"

    runtime_view.render(source, out, project="deepstream")

    page = out.read_text(encoding="utf-8")
    assert "<title>Control server — runtime architecture</title>" in page
    assert "app.main" in page


def test_runtime_render_falls_back_to_the_project_name(tmp_path):
    model = {"canvas": [100, 100], "zones": [], "nodes": [], "edges": []}
    source = tmp_path / "runtime.json"
    source.write_text(json.dumps(model), encoding="utf-8")
    out = tmp_path / "architecture.html"

    runtime_view.render(source, out, project="control-server")

    assert (
        "<title>control-server — runtime architecture</title>"
        in out.read_text(encoding="utf-8")
    )


def test_env_prints_the_resolved_project(capsys):
    assert arch.main(["env"]) == 0
    output = capsys.readouterr().out
    assert "project:" in output
    assert "design:" in output


def test_classes_ls_filters_by_kind(tmp_path, monkeypatch, capsys):
    _fake_project(tmp_path, monkeypatch)

    assert arch.main(["classes", "ls", "--kind", "interface"]) == 0
    assert "ClassLegend" not in capsys.readouterr().out


def test_show_and_deps_name_a_missing_class_once(tmp_path, monkeypatch, capsys):
    _fake_project(tmp_path, monkeypatch)

    assert arch.main(["classes", "show", "Nope"]) == 1
    assert "no class" in capsys.readouterr().err
    assert arch.main(["classes", "deps", "Nope"]) == 1


def test_render_classes_writes_the_page(tmp_path, monkeypatch):
    _fake_project(tmp_path, monkeypatch)
    monkeypatch.setattr(arch, "DOCS", tmp_path)

    assert arch.main(["render", "classes"]) == 0
    assert (tmp_path / "diagrams.html").is_file()


def test_render_runtime_writes_the_page(tmp_path, monkeypatch):
    model = {
        "title": "demo",
        "canvas": [400, 200],
        "zones": [{"id": "z", "x": 0, "y": 0, "w": 200, "h": 100, "label": "zone"}],
        "nodes": [
            {
                "id": "demo", "x": 10, "y": 10, "w": 80, "h": 40,
                "label": "demo", "sub": "x", "note": "1", "tone": "entry",
            }
        ],
        "edges": [
            {
                "from": "demo", "side": "bottom", "to": "demo", "to_side": "top",
                "kind": "dash", "label": "l", "dx": 0, "dy": 0,
            }
        ],
    }
    runtime = tmp_path / "runtime.json"
    runtime.write_text(json.dumps(model), encoding="utf-8")
    monkeypatch.setattr(arch, "RUNTIME", runtime)
    monkeypatch.setattr(arch, "DOCS", tmp_path)

    assert arch.main(["runtime", "render"]) == 0
    page = (tmp_path / "ARCHITECTURE.html").read_text(encoding="utf-8")
    assert "<svg" in page
    assert "zone" in page


def test_runtime_ls_and_show(tmp_path, monkeypatch, capsys):
    model = {
        "title": "demo", "canvas": [400, 200], "zones": [],
        "nodes": [{"id": "demo", "x": 0, "y": 0, "w": 1, "h": 1, "label": "demo",
                   "sub": "s", "note": None, "tone": "entry", "package": "demo"}],
        "edges": [],
    }
    runtime = tmp_path / "runtime.json"
    runtime.write_text(json.dumps(model), encoding="utf-8")
    monkeypatch.setattr(arch, "RUNTIME", runtime)

    assert arch.main(["runtime", "ls"]) == 0
    assert "demo" in capsys.readouterr().out
    assert arch.main(["runtime", "show", "demo"]) == 0
    assert arch.main(["runtime", "show", "ghost"]) == 1


def test_docs_validate_names_a_missing_spec(tmp_path, monkeypatch, capsys):
    _fake_project(tmp_path, monkeypatch)
    monkeypatch.setattr(arch, "SPECS", {"missing.md": "rule_check_osd"})
    monkeypatch.setattr(arch, "SPEC_DIR", tmp_path / "specs")
    (tmp_path / "specs").mkdir()

    assert arch.main(["docs", "validate"]) == 1
    assert "missing" in capsys.readouterr().out


def test_overlay_validate_reports_every_bad_field(tmp_path):
    data = {
        "nodes": [{"id": "a.B", "subsystem": "a", "stereotype": "weird", "layer": "outer"}],
        "edges": [{"from": "a.B", "to": "ghost", "kind": "bogus", "since": "2000-01-01"}],
        "annotations": {},
    }

    problems = overlay.validate(data, set(), set(), strict=True)

    assert any("bad stereotype" in problem for problem in problems)
    assert any("bad layer" in problem for problem in problems)
    assert any("bad kind" in problem for problem in problems)
    assert any("unknown node" in problem for problem in problems)


def test_class_relations_cover_extends_and_implements(tmp_path):
    root = tmp_path / "pkg"
    (root / "demo").mkdir(parents=True)
    (root / "demo" / "base.py").write_text(
        "from abc import ABC, abstractmethod\n\n"
        "class Base(ABC):\n    @abstractmethod\n    def run(self): ...\n",
        encoding="utf-8",
    )
    (root / "demo" / "child.py").write_text(
        "from .base import Base\n\nclass Child(Base):\n    def run(self):\n        return 1\n",
        encoding="utf-8",
    )
    classes = class_model.scan(root, ("demo",))
    edges = class_model.relations(classes)

    assert ("Child", "Base", "implements") in edges


def test_classes_validate_on_a_clean_fake_project(tmp_path, monkeypatch):
    _fake_project(tmp_path, monkeypatch)

    assert arch.main(["classes", "validate"]) == 0


def test_classes_validate_names_a_core_to_shell_edge(tmp_path, monkeypatch, capsys):
    root = tmp_path / "pkg"
    for name, body in {
        "demo/core/rules.py": (
            "class Rules:\n"
            "    def __init__(self, speaker: Speaker):\n"
            "        self.speaker = speaker\n"
        ),
        "demo/shell/speaker.py": "class Speaker:\n    pass\n",
    }.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
    monkeypatch.setattr(arch, "PIPELINE", root)
    monkeypatch.setattr(arch.paths, "DESIGN", tmp_path / "design.json")
    monkeypatch.setattr(
        class_model, "DIAGRAMS", (("01", "demo", ("demo",)),)
    )

    assert arch.main(["classes", "validate"]) == 1
    assert "core depends on shell" in capsys.readouterr().out


def test_classes_validate_refuses_a_missing_tree(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(arch, "PIPELINE", tmp_path / "gone")

    assert arch.main(["classes", "validate"]) == 1
    assert "no class tree" in capsys.readouterr().out


def test_render_all_writes_both_views(tmp_path, monkeypatch):
    _fake_project(tmp_path, monkeypatch)
    model = {"title": "demo", "canvas": [200, 100], "zones": [], "nodes": [], "edges": []}
    runtime = tmp_path / "runtime.json"
    runtime.write_text(json.dumps(model), encoding="utf-8")
    monkeypatch.setattr(arch, "RUNTIME", runtime)
    monkeypatch.setattr(arch, "DOCS", tmp_path)

    assert arch.main(["render", "all"]) == 0
    assert (tmp_path / "diagrams.html").is_file()
    assert (tmp_path / "ARCHITECTURE.html").is_file()


def test_runtime_validate_names_an_unboxed_subsystem(tmp_path, monkeypatch, capsys):
    (tmp_path / "pipeline" / "orphan").mkdir(parents=True)
    model = {"title": "t", "canvas": [1, 1], "zones": [], "nodes": [], "edges": []}
    runtime = tmp_path / "runtime.json"
    runtime.write_text(json.dumps(model), encoding="utf-8")
    monkeypatch.setattr(arch, "RUNTIME", runtime)
    monkeypatch.setattr(arch, "PIPELINE", tmp_path / "pipeline")

    assert arch.main(["runtime", "validate"]) == 1
    assert "orphan" in capsys.readouterr().out


def test_add_node_and_edge_reject_bad_input(tmp_path, monkeypatch, capsys):
    _fake_project(tmp_path, monkeypatch)
    assert arch.main(["classes", "add", "node"]) == 1
    assert arch.main(["classes", "add", "node", "x.Y", "--subsystem", "nope"]) == 1
    assert arch.main(["classes", "add", "edge", "--from", "a"]) == 1
    assert arch.main(["classes", "add", "edge", "one", "two", "three"]) == 0


def test_remove_reports_nothing_to_remove(tmp_path, monkeypatch, capsys):
    _fake_project(tmp_path, monkeypatch)
    assert arch.main(["classes", "remove", "node", "ghost.Node"]) == 1
    assert "nothing removed" in capsys.readouterr().err


def test_annotate_and_diff_report_design_only_entries(tmp_path, monkeypatch, capsys):
    _fake_project(tmp_path, monkeypatch)
    assert arch.main(["classes", "annotate", "rule_check_osd.legend.ClassLegend", "--note", "why"]) == 0
    assert arch.main(["classes", "diff"]) == 0
    assert "no design-only nodes or edges" in capsys.readouterr().out


def test_overlay_helpers_cover_removal_and_merge(tmp_path):
    data = {"nodes": [], "edges": [], "annotations": {}}
    overlay.annotate(data, "pkg.Thing", "note", "shell")
    assert data["annotations"]["pkg.Thing"] == {"note": "note", "layer": "shell"}
    overlay.add_edge(data, {"from": "A", "to": "B", "kind": "dependency", "since": "2026-01-01"})
    assert overlay.remove_edge(data, "A", "B") is True
    assert overlay.remove_edge(data, "A", "B") is False
    assert overlay.remove_node(data, "missing") is False
    assert overlay.age_days("not-a-date") == -1

    info = class_model.ClassInfo(name="Thing", module="pkg/thing", group="pkg")
    classes = {"Thing": info}
    edges: list = []
    overlay.merge(classes, edges, data, "pkg", lambda node, name: info)
    assert classes["Thing"].layer_override == "shell"


def test_overlay_diff_marks_stale_edges_and_nodes():
    data = {
        "nodes": [{"id": "pkg.A", "subsystem": "pkg", "since": "2026-01-01"}],
        "edges": [{"from": "pkg.A", "to": "pkg.B", "kind": "dependency"}],
        "annotations": {},
    }

    rows = overlay.diff({"pkg.A"}, {("pkg.A", "pkg.B")}, data)

    assert any(row.startswith("stale overlay: pkg.A") for row in rows)
    assert any(row.startswith("stale overlay edge: pkg.A -> pkg.B") for row in rows)


def test_rendering_is_deterministic(tmp_path, monkeypatch):
    _fake_project(tmp_path, monkeypatch)
    monkeypatch.setattr(arch, "DOCS", tmp_path)
    first = tmp_path / "one.html"
    second = tmp_path / "two.html"

    arch.class_map.render(arch.PIPELINE, first, arch._overlay(), project="demo")
    arch.class_map.render(arch.PIPELINE, second, arch._overlay(), project="demo")

    assert first.read_text(encoding="utf-8") == second.read_text(encoding="utf-8")
