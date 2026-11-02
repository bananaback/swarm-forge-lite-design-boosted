"""Rule I1 — the installer writes only where the tier boundary allows.

A tmp pack is a real git repository. After an install, `git status` must show
nothing: the config and scratch are ignored, and the design folder lives in the
project, outside the pack.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
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


def _fixture(tmp_path: Path) -> tuple[Path, Path]:
    pack = tmp_path / "pack"
    project = tmp_path / "proj"
    for name in ("runtime.json", "overlay.json", "policy.json"):
        _write(pack / "examples" / "design" / name, "{}")
    _write(pack / "PROJECT.md.example", "# Project\n\n## Environment\n\nx\n")
    _write(pack / ".gitignore", "tmp/\nlocal/\nconfig/pack.local.json\nPROJECT.md\n")
    subprocess.run(["git", "init", "-q", str(pack)], check=True)
    subprocess.run(["git", "-C", str(pack), "add", "-A"], check=True)
    subprocess.run(
        [
            "git", "-C", str(pack),
            "-c", "user.name=test", "-c", "user.email=test@example.com",
            "-c", "commit.gpgsign=false",
            "commit", "-q", "-m", "seed",
        ],
        check=True,
    )
    _write(project / "app" / "demo" / "core.py", "class Thing:\n    pass\n")
    return pack, project


def test_an_install_leaves_the_harness_repository_clean(tmp_path):
    pack, project = _fixture(tmp_path)
    install = _install()

    install.apply_answers(
        pack,
        {
            "name": "demo",
            "root": str(project),
            "source_roots": ["app"],
            "design_root": "design",
        },
    )

    status = subprocess.run(
        ["git", "-C", str(pack), "status", "--porcelain"],
        capture_output=True, text=True, check=False,
    ).stdout
    assert status.strip() == "", status
    assert (project / "design" / "runtime.json").is_file()
    assert json.loads((pack / "config" / "pack.local.json").read_text())["projects"]["demo"]
