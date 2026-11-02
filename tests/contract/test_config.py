"""Rules 32 and 35 — one config rule for every tool.

Precedence is `SWARM_CONFIG` > `config/pack.local.json` >
`config/pack.json`, values may carry the `<PACK>` token, a missing config names
the installer instead of raising a traceback, and `design_root` selects the
project-owned design folder with the legacy path as fallback.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

PACK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PACK / "tools" / "shared"))

import packconfig  # noqa: E402


def _write_config(path: Path, **projects) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "selector_env": "PACK_PROJECT",
                "default_project": next(iter(projects)),
                "projects": projects,
            }
        ),
        encoding="utf-8",
    )
    return path


def _project(base: Path | None = None, **extra) -> dict:
    """A minimal project entry; absolute under `base`, else with <PACK> tokens."""
    root = f"{base}/demo" if base else "<PACK>/demo"
    tmp = f"{base}/tmp/demo" if base else "<PACK>/tmp/demo"
    entry = {"project_root": root, "source_roots": ["app"], "artifacts_root": tmp}
    entry.update(extra)
    return entry


def test_local_config_wins_over_the_legacy_file(tmp_path):
    _write_config(tmp_path / "config" / "pack.json", demo=_project())
    local = _write_config(tmp_path / "config" / "pack.local.json", demo=_project())

    assert packconfig.config_path(tmp_path) == local


def test_legacy_config_is_the_fallback(tmp_path):
    legacy = _write_config(tmp_path / "config" / "pack.json", demo=_project())

    assert packconfig.config_path(tmp_path) == legacy


def test_env_override_wins_over_both(tmp_path, monkeypatch):
    custom = _write_config(tmp_path / "elsewhere" / "custom.json", demo=_project())
    monkeypatch.setenv("SWARM_CONFIG", str(custom))

    assert packconfig.config_path(PACK) == custom.resolve()


def test_missing_config_names_the_installer(tmp_path, monkeypatch):
    monkeypatch.delenv("SWARM_CONFIG", raising=False)

    with pytest.raises(packconfig.ConfigError) as error:
        packconfig.config_path(tmp_path)

    assert "tools/install.py" in str(error.value)


def test_pack_token_expands_to_the_pack_root(tmp_path):
    _write_config(tmp_path / "config" / "pack.json", demo=_project())
    config = packconfig.load(tmp_path)

    assert config["projects"]["demo"]["project_root"] == f"{tmp_path}/demo"
    assert config["projects"]["demo"]["artifacts_root"] == f"{tmp_path}/tmp/demo"


def test_select_prefers_the_selector_then_the_default(tmp_path, monkeypatch):
    _write_config(tmp_path / "config" / "pack.json", demo=_project())
    config = packconfig.load(tmp_path)

    monkeypatch.setenv("PACK_PROJECT", "demo")
    assert packconfig.select(config) == ("demo", "PACK_PROJECT")

    monkeypatch.delenv("PACK_PROJECT")
    assert packconfig.select(config) == ("demo", "default_project")


def test_select_rejects_an_unknown_project(tmp_path, monkeypatch):
    _write_config(tmp_path / "config" / "pack.json", demo=_project())
    config = packconfig.load(tmp_path)

    monkeypatch.setenv("PACK_PROJECT", "ghost")

    with pytest.raises(packconfig.ConfigError) as error:
        packconfig.select(config)

    assert "ghost" in str(error.value)


def test_env_reports_the_project_owned_design_folder(run_tool, tmp_path):
    config = _write_config(
        tmp_path / "config" / "pack.json",
        demo=_project(tmp_path, design_root="design"),
    )

    result = run_tool(
        "tools/design/arch.py",
        "env",
        env={"SWARM_CONFIG": str(config), "PACK_PROJECT": "demo"},
    )

    assert result.returncode == 0, result.stderr
    assert f"design:       {tmp_path}/demo/design" in result.stdout
    assert "legacy" not in result.stdout


def test_env_warns_about_the_legacy_design_folder(run_tool, tmp_path):
    config = _write_config(
        tmp_path / "config" / "pack.json", demo=_project(tmp_path)
    )

    result = run_tool(
        "tools/design/arch.py",
        "env",
        env={"SWARM_CONFIG": str(config), "PACK_PROJECT": "demo"},
    )

    assert result.returncode == 0, result.stderr
    assert "warning:" in result.stdout
    assert "legacy design path" in result.stdout


def test_a_missing_config_fails_with_a_sentence_not_a_traceback(run_tool, tmp_path):
    result = run_tool(
        "tools/design/arch.py",
        "env",
        env={"SWARM_CONFIG": str(tmp_path / "does-not-exist.json")},
    )

    assert result.returncode == 1
    assert "tools/install.py" in result.stderr
    assert "Traceback" not in result.stderr


def _reload_paths():
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "paths_under_test", PACK / "tools" / "design" / "paths.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_paths_resolve_the_design_folder_from_design_root(tmp_path, monkeypatch):
    config = _write_config(
        tmp_path / "config" / "pack.json",
        demo=_project(tmp_path, design_root="design"),
    )
    monkeypatch.setenv("SWARM_CONFIG", str(config))
    monkeypatch.setenv("PACK_PROJECT", "demo")

    paths = _reload_paths()

    assert paths.LEGACY_DESIGN is False
    assert paths.RUNTIME.name == "runtime.json"
    assert paths.DESIGN.name == "overlay.json"
    assert paths.POLICY.name == "policy.json"


def test_paths_fall_back_to_the_legacy_design_files(tmp_path, monkeypatch):
    config = _write_config(tmp_path / "config" / "pack.json", demo=_project(tmp_path))
    monkeypatch.setenv("SWARM_CONFIG", str(config))
    monkeypatch.setenv("PACK_PROJECT", "demo")

    paths = _reload_paths()

    assert paths.LEGACY_DESIGN is True
    assert paths.DESIGN.name == "design.json"
    assert paths.POLICY.name == "umlview.json"
