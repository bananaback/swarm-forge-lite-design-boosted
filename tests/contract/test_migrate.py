"""The design migration is additive: it copies, it never moves or overwrites."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

PACK = Path(__file__).resolve().parents[2]


def _migrate():
    spec = importlib.util.spec_from_file_location("migrate", PACK / "tools" / "migrate.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write(path: Path, text: str = "{}") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _fixture(tmp_path: Path) -> tuple[Path, dict]:
    pack = tmp_path / "pack"
    project = tmp_path / "proj"
    _write(pack / "architecture" / "demo" / "runtime.json", '{"nodes": []}')
    _write(pack / "architecture" / "demo" / "design.json", '{"nodes": []}')
    policy = _write(project / "umlview.json", '{"title": "demo"}')
    assert policy.is_file()
    config = {
        "projects": {
            "demo": {"project_root": str(project), "design_root": "design"}
        }
    }
    return pack, config


def test_dry_run_lists_copies_and_writes_nothing(tmp_path):
    pack, config = _fixture(tmp_path)
    migrate = _migrate()

    rows = migrate.plan(pack, config, ["demo"])

    assert any("copy ->" in action for _, action, _ in rows)
    assert not (tmp_path / "proj" / "design").exists()


def test_apply_copies_and_keeps_the_originals(tmp_path):
    pack, config = _fixture(tmp_path)
    migrate = _migrate()

    migrate.apply(pack, config, ["demo"])

    design = tmp_path / "proj" / "design"
    assert (design / "runtime.json").is_file()
    assert (design / "overlay.json").is_file()
    assert (design / "policy.json").is_file()
    assert (pack / "architecture" / "demo" / "runtime.json").is_file()
    assert (tmp_path / "proj" / "umlview.json").is_file()


def test_second_run_changes_nothing(tmp_path):
    pack, config = _fixture(tmp_path)
    migrate = _migrate()
    migrate.apply(pack, config, ["demo"])
    before = (tmp_path / "proj" / "design" / "runtime.json").read_text()

    rows = migrate.apply(pack, config, ["demo"])

    assert all("kept" in action or "absent" in action for _, action, _ in rows)
    assert (tmp_path / "proj" / "design" / "runtime.json").read_text() == before


def test_a_project_without_design_root_is_skipped(tmp_path):
    pack, _config = _fixture(tmp_path)
    migrate = _migrate()
    config = {"projects": {"demo": {"project_root": str(tmp_path / "proj")}}}

    rows = migrate.plan(pack, config, ["demo"])

    assert len(rows) == 1
    assert "skip" in rows[0][1]


def test_the_config_shape_is_read_by_plan(tmp_path):
    pack, config = _fixture(tmp_path)
    migrate = _migrate()

    rows = migrate.plan(pack, config, ["demo"])

    assert {action.split(" ->")[0] for _, action, _ in rows} <= {"copy", "absent"}
    assert json.loads((pack / "architecture" / "demo" / "design.json").read_text()) == {
        "nodes": []
    }
