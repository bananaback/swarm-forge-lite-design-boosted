"""`doctor` names the blocking check and never fails on a warning."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

PACK = Path(__file__).resolve().parents[2]


def _doctor():
    spec = importlib.util.spec_from_file_location("doctor", PACK / "tools" / "doctor.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write(path: Path, text: str = "") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _fixture(tmp_path: Path) -> tuple[Path, dict]:
    pack = tmp_path / "pack"
    project = tmp_path / "proj"
    _write(project / "app" / "demo.py", "class Thing:\n    pass\n")
    _write(project / "tests" / "unit" / "test_thing.py", "def test_x():\n    pass\n")
    _write(project / "docs" / "specs" / "01-demo.md", "# demo\n")
    _write(project / "design" / "runtime.json", '{"nodes": []}')
    _write(project / "design" / "overlay.json", '{"nodes": []}')
    _write(pack / "PROJECT.md", "# Project\n\n## Environment\n\nx\n")
    _write(
        pack / "config" / "pack.schema.json",
        (PACK / "config" / "pack.schema.json").read_text(),
    )
    config = {
        "default_project": "demo",
        "projects": {
            "demo": {
                "project_root": str(project),
                "source_roots": ["app"],
                "class_root": "app",
                "docs_root": "docs",
                "design_root": "design",
                "specs": {"01-demo.md": "demo"},
                "unit_paths": "tests/unit",
            }
        },
    }
    _write(pack / "config" / "pack.json", json.dumps(config))
    return pack, config


def test_a_well_formed_install_has_no_failures(tmp_path):
    pack, config = _fixture(tmp_path)

    rows = _doctor().run(pack, config, "demo")

    assert [text for status, text in rows if status == "fail"] == []


def test_a_missing_spec_is_a_failure(tmp_path):
    pack, config = _fixture(tmp_path)
    (tmp_path / "proj" / "docs" / "specs" / "01-demo.md").unlink()

    rows = _doctor().run(pack, config, "demo")

    assert any(status == "fail" and "01-demo.md" in text for status, text in rows)


def test_a_missing_project_tree_is_a_failure(tmp_path):
    pack, config = _fixture(tmp_path)
    config["projects"]["demo"]["project_root"] = str(tmp_path / "gone")

    rows = _doctor().run(pack, config, "demo")

    assert any(status == "fail" and "project tree missing" in text for status, text in rows)


def test_an_invalid_config_is_a_failure(tmp_path):
    pack, config = _fixture(tmp_path)
    config["projects"]["demo"] = {"project_root": str(tmp_path / "proj")}

    rows = _doctor().run(pack, config, "demo")

    assert any(status == "fail" and "source_roots" in text for status, text in rows)


def test_a_git_checkout_reports_its_state(tmp_path):
    import subprocess

    pack, config = _fixture(tmp_path)
    subprocess.run(["git", "init", "-q", str(pack)], check=True)
    subprocess.run(["git", "-C", str(pack), "add", "-A"], check=True)
    subprocess.run(
        ["git", "-C", str(pack), "-c", "user.name=t", "-c", "user.email=t@e",
         "-c", "commit.gpgsign=false", "commit", "-q", "-m", "seed"],
        check=True,
    )

    (pack / "PROJECT.md").write_text("# changed\n", encoding="utf-8")

    rows = _doctor().run(pack, config, "demo")

    assert any("modified harness file" in text for _, text in rows)


def test_capabilities_can_be_disabled_or_unknown(tmp_path):
    pack, config = _fixture(tmp_path)
    config["projects"]["demo"]["capabilities"] = {"duplication": False, "mystery": True}

    rows = _doctor().run(pack, config, "demo")

    texts = [text for _, text in rows]
    assert any("duplication: disabled" in text for text in texts)
    assert any("unknown capability" in text for text in texts)


def test_main_returns_one_on_a_blocking_failure(tmp_path, monkeypatch, capsys):
    pack, config = _fixture(tmp_path)
    config["projects"]["demo"]["project_root"] = str(tmp_path / "gone")
    (pack / "config" / "pack.json").write_text(json.dumps(config))
    doctor = _doctor()
    monkeypatch.setattr(doctor, "PACK", pack)
    monkeypatch.setenv("PACK_PROJECT", "demo")

    assert doctor.main([]) == 1
    assert "fail" in capsys.readouterr().out
