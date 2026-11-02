"""CLI entry points, exercised in-process so coverage sees them.

Each test builds its own pack under tmp_path, points the module's `PACK` at it,
and calls `main`. These are the branches a subprocess test cannot measure.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

PACK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PACK / "tools" / "shared"))


def _write(path: Path, text: str = "") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _module(name: str):
    spec = importlib.util.spec_from_file_location(name, PACK / "tools" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _pack(tmp_path: Path, *, design: bool = True) -> tuple[Path, Path]:
    pack = tmp_path / "pack"
    project = tmp_path / "proj"
    _write(project / "app" / "demo" / "core.py", "class Thing:\n    pass\n")
    _write(project / "tests" / "unit" / "test_core.py", "def test_x():\n    assert True\n")
    _write(project / "docs" / "specs" / "01-demo.md", "# demo\n")
    if design:
        _write(project / "design" / "runtime.json", '{"nodes": []}')
        _write(project / "design" / "overlay.json", '{"nodes": []}')
        _write(project / "design" / "policy.json", '{"title": "demo"}')
    _write(pack / "PROJECT.md", "# Project\n\n## Environment\n\nx\n")
    _write(pack / "config" / "pack.schema.json", (PACK / "config" / "pack.schema.json").read_text())
    for name in ("runtime.json", "overlay.json", "policy.json"):
        _write(pack / "examples" / "design" / name, "{}")
    _write(pack / "PROJECT.md.example", "# Project\n\n## Environment\n\nx\n")
    _write(pack / ".gitignore", "")
    config = {
        "default_project": "demo",
        "projects": {
            "demo": {
                "project_root": str(project),
                "source_roots": ["app"],
                "class_root": "app",
                "docs_root": "docs",
                "design_root": "design",
                "unit_paths": "tests/unit",
                "specs": {"01-demo.md": "demo"},
                "artifacts_root": "<PACK>/tmp/demo",
                "gates": {"ok": ["true"], "bad": ["false"]},
            }
        },
    }
    _write(pack / "config" / "pack.json", json.dumps(config))
    return pack, project


def test_gate_main_lists_and_dry_runs(tmp_path, monkeypatch, capsys):
    pack, _ = _pack(tmp_path)
    gate = _module("gate")
    monkeypatch.setattr(gate, "PACK", pack)
    monkeypatch.setenv("PACK_PROJECT", "demo")

    assert gate.main(["--list"]) == 0
    assert "ok" in capsys.readouterr().out
    assert gate.main(["ok", "--dry-run"]) == 0
    assert gate.main(["bad"]) == 1


def test_gate_main_reports_an_unknown_gate(tmp_path, monkeypatch, capsys):
    pack, _ = _pack(tmp_path)
    gate = _module("gate")
    monkeypatch.setattr(gate, "PACK", pack)
    monkeypatch.setenv("PACK_PROJECT", "demo")

    assert gate.main(["nope"]) == 1
    assert "unknown gate" in capsys.readouterr().err


def test_doctor_main_is_green_and_json(tmp_path, monkeypatch, capsys):
    pack, _ = _pack(tmp_path)
    doctor = _module("doctor")
    monkeypatch.setattr(doctor, "PACK", pack)
    monkeypatch.setenv("PACK_PROJECT", "demo")

    assert doctor.main(["--json"]) == 0
    rows = json.loads(capsys.readouterr().out)
    assert all("status" in row for row in rows)


def test_install_main_inspect_then_apply(tmp_path, monkeypatch, capsys):
    pack, project = _pack(tmp_path)
    install = _module("install")
    monkeypatch.setattr(install, "PACK", pack)

    assert install.main(["inspect", "--root", str(project)]) == 0
    brief = capsys.readouterr().out
    assert "Install brief" in brief

    answers = tmp_path / "answers.json"
    answers.write_text(json.dumps({"name": "demo", "root": str(project)}))
    assert install.main(["apply", "--answers", str(answers)]) == 0
    assert (pack / "config" / "pack.local.json").is_file()


def test_install_main_reports_bad_answers(tmp_path, monkeypatch, capsys):
    pack, _ = _pack(tmp_path)
    install = _module("install")
    monkeypatch.setattr(install, "PACK", pack)
    bad = tmp_path / "bad.json"
    bad.write_text("{not json")

    assert install.main(["apply", "--answers", str(bad)]) == 1
    assert "install:" in capsys.readouterr().err


def test_migrate_main_dry_run(tmp_path, monkeypatch, capsys):
    pack, project = _pack(tmp_path, design=False)
    _write(pack / "architecture" / "demo" / "runtime.json", "{}")
    migrate = _module("migrate")
    monkeypatch.setattr(migrate, "PACK", pack)
    monkeypatch.setenv("PACK_PROJECT", "demo")

    assert migrate.main(["--dry-run"]) == 0
    assert "copy" in capsys.readouterr().out
    assert not (project / "design").exists()


def test_update_report_and_state_round_trip(tmp_path):
    update = _module("update")
    state = {"commit": "abc", "migrations": []}
    update.write_state(tmp_path, state)

    assert update.read_state(tmp_path)["commit"] == "abc"
    assert "up to date" in update.report({"error": "", "commits": [], "files": [], "dirty": [], "diverged": False})
    assert update.risk_of("protocol/x.md") == "behavior"
    assert update.risk_of("config/pack.json") == "legacy"
    assert update.risk_of("migrations/0001.py") == "migration"
    assert update.risk_of("tests/a.py") == "tests"
    assert update.risk_of("README.md") == "docs"
