"""`install.py` detects a tree, then writes only what the answers allow."""

from __future__ import annotations

import importlib.util
import json
import shutil
from pathlib import Path

PACK = Path(__file__).resolve().parents[2]


def _install():
    spec = importlib.util.spec_from_file_location("install", PACK / "tools" / "install.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write(path: Path, text: str = "") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _tree(tmp_path: Path) -> Path:
    root = tmp_path / "toy"
    _write(root / "app" / "demo" / "core.py", "class Thing:\n    pass\n")
    _write(root / "tests" / "unit" / "test_core.py", "def test_x():\n    pass\n")
    _write(root / "tests" / "features" / "demo.feature", "Feature: demo\n")
    _write(root / "docs" / "specs" / "01-demo.md", "# demo\n")
    return root


def _pack(tmp_path: Path) -> Path:
    pack = tmp_path / "pack"
    for name in ("runtime.json", "overlay.json", "policy.json"):
        _write(pack / "examples" / "design" / name, "{}")
    _write(pack / "PROJECT.md.example", "# Project\n\n## Environment\n\nx\n")
    _write(pack / ".gitignore", "tmp/\n")
    return pack


def test_inspect_detects_the_usual_layout(tmp_path):
    install = _install()
    root = _tree(tmp_path)

    report = install.detect(root)

    assert report["entry"]["source_roots"] == ["app"]
    assert report["entry"]["unit_paths"] == "tests/unit"
    assert report["entry"]["features"] == "tests/features"
    assert report["entry"]["specs"] == {"01-demo.md": "demo"}
    assert report["entry"]["acceptance_command"] == ""


def test_inspect_asks_only_for_what_it_cannot_find(tmp_path):
    install = _install()
    root = _tree(tmp_path)

    report = install.detect(root)

    assert report["questions"] == ["acceptance_command"]


def test_apply_writes_config_design_and_project_record(tmp_path):
    install = _install()
    pack = _pack(tmp_path)
    root = _tree(tmp_path)
    answers = {
        "name": "demo",
        "root": str(root),
        "source_roots": ["app"],
        "class_root": "app",
        "docs_root": "docs",
        "design_root": "design",
        "unit_paths": "tests/unit",
        "artifacts_root": "<PACK>/tmp/demo",
    }

    install.apply_answers(pack, answers)

    config = json.loads((pack / "config" / "pack.local.json").read_text())
    assert config["projects"]["demo"]["project_root"]
    assert (root / "design" / "runtime.json").is_file()
    assert (root / "design" / "overlay.json").is_file()
    assert (root / "design" / "policy.json").is_file()
    assert (pack / "PROJECT.md").is_file()
    assert (pack / "tmp" / "demo").is_dir()
    assert "config/pack.local.json" in (pack / ".gitignore").read_text()


def test_apply_is_idempotent(tmp_path):
    install = _install()
    pack = _pack(tmp_path)
    root = _tree(tmp_path)
    answers = {"name": "demo", "root": str(root), "source_roots": ["app"], "design_root": "design"}

    install.apply_answers(pack, answers)
    before = (root / "design" / "runtime.json").read_text()
    actions = install.apply_answers(pack, answers)

    assert any("kept" in action for action in actions)
    assert any("config:" in action for action in actions)
    assert (root / "design" / "runtime.json").read_text() == before


def test_dry_run_writes_nothing(tmp_path):
    install = _install()
    pack = _pack(tmp_path)
    root = _tree(tmp_path)
    answers = {"name": "demo", "root": str(root), "source_roots": ["app"], "design_root": "design"}

    install.apply_answers(pack, answers, dry_run=True)

    assert not (pack / "config" / "pack.local.json").exists()
    assert not (root / "design").exists()


def test_answers_without_a_name_are_refused(tmp_path):
    install = _install()
    pack = _pack(tmp_path)

    try:
        install.apply_answers(pack, {"root": str(tmp_path / "x")})
    except ValueError as error:
        assert "name" in str(error)
    else:
        raise AssertionError("apply accepted answers without a name")


def test_a_missing_project_record_is_copied_from_the_example(tmp_path):
    install = _install()
    pack = _pack(tmp_path)
    root = _tree(tmp_path)
    (pack / "PROJECT.md.example").unlink()

    try:
        install.apply_answers(pack, {"name": "demo", "root": str(root)})
    except OSError:
        pass

    assert not (pack / "PROJECT.md").exists()
