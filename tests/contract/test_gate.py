"""Rules 29 and 31 — the gate runner maps names to project commands.

The protocol names gates; the project owns the command. These tests pin the
mapping, the override, and the promise that the underlying exit code is the
gate's exit code.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

PACK = Path(__file__).resolve().parents[2]


def _gate_module():
    spec = importlib.util.spec_from_file_location("gate", PACK / "tools" / "gate.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _entry(**extra) -> dict:
    entry = {
        "project_root": "proj",
        "source_roots": ["app"],
        "unit_paths": "tests/unit",
        "lint_paths": ".",
        "artifacts_root": "tmp",
        "acceptance_command": "python3 tests/acceptance/run_acceptance.py",
    }
    entry.update(extra)
    return entry


def test_defaults_cover_the_python_reference(tmp_path):
    gate = _gate_module()

    gates = gate.resolve(tmp_path / "proj", _entry())

    assert set(gates) >= {
        "lint",
        "format_check",
        "unit",
        "acceptance",
        "dry",
        "crap",
        "coverage",
        "lcov",
    }
    assert gates["unit"][0][-1] == "tests/unit"


def test_config_overrides_a_default(tmp_path):
    gate = _gate_module()
    entry = _entry(gates={"unit": ["echo", "custom"]})

    gates = gate.resolve(tmp_path / "proj", entry)

    assert gates["unit"][0] == ["echo", "custom"]
    assert "config" in gates["unit"][1]


def test_project_token_expands(tmp_path):
    gate = _gate_module()

    command = gate._expand(["run", "<PROJECT>/x"], tmp_path / "proj")

    assert command == ["run", f"{tmp_path}/proj/x"]


def _config(tmp_path: Path, gate_command: list[str]) -> Path:
    (tmp_path / "proj").mkdir(parents=True, exist_ok=True)
    config = tmp_path / "config" / "pack.json"
    config.parent.mkdir(parents=True, exist_ok=True)
    config.write_text(
        json.dumps(
            {
                "selector_env": "PACK_PROJECT",
                "default_project": "demo",
                "projects": {
                    "demo": {
                        "project_root": str(tmp_path / "proj"),
                        "source_roots": ["app"],
                        "unit_paths": "tests/unit",
                        "artifacts_root": "tmp",
                        "gates": {"boom": gate_command},
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    return config


def test_the_gate_exit_code_is_returned_unchanged(run_tool, tmp_path):
    config = _config(tmp_path, ["python3", "-c", "import sys; sys.exit(7)"])

    result = run_tool("tools/gate.py", "boom", env={"SWARM_CONFIG": str(config)})

    assert result.returncode == 7


def test_an_unknown_gate_is_a_user_error(run_tool, tmp_path):
    config = _config(tmp_path, ["true"])

    result = run_tool("tools/gate.py", "nope", env={"SWARM_CONFIG": str(config)})

    assert result.returncode == 1
    assert "unknown gate" in result.stderr


def test_dry_run_prints_the_command_and_runs_nothing(run_tool, tmp_path):
    config = _config(tmp_path, ["false"])

    result = run_tool(
        "tools/gate.py", "boom", "--dry-run", env={"SWARM_CONFIG": str(config)}
    )

    assert result.returncode == 0
    assert "command:" in result.stderr


def test_a_disabled_capability_refuses_instead_of_passing(run_tool, tmp_path):
    (tmp_path / "proj").mkdir(parents=True, exist_ok=True)
    config = tmp_path / "config" / "pack.json"
    config.parent.mkdir(parents=True, exist_ok=True)
    config.write_text(
        json.dumps(
            {
                "default_project": "demo",
                "projects": {
                    "demo": {
                        "project_root": str(tmp_path / "proj"),
                        "source_roots": ["app"],
                        "artifacts_root": "tmp",
                        "capabilities": {"duplication": False},
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    result = run_tool("tools/gate.py", "dry", env={"SWARM_CONFIG": str(config)})

    assert result.returncode == 1
    assert "disabled" in result.stderr
