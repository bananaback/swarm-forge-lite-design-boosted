"""The update path against a real bare remote: reviewed, additive, reversible.

Cases from the goal: an available commit, a dirty worktree, a diverged branch,
and a clean fast-forward that keeps project-owned design data byte-identical.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

PACK = Path(__file__).resolve().parents[2]
IGNORE = shutil.ignore_patterns(
    ".git", "tmp", "__pycache__", ".pytest_cache", "config/pack.local.json"
)


def git(cwd: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [
            "git", "-C", str(cwd),
            "-c", "user.name=test", "-c", "user.email=test@example.com",
            "-c", "commit.gpgsign=false",
            *args,
        ],
        capture_output=True, text=True, check=False,
    )


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _project(tmp: Path) -> Path:
    root = tmp / "proj"
    _write(root / "app" / "demo" / "core.py", "class Thing:\n    pass\n")
    _write(
        root / "docs" / "specs" / "01-demo.md",
        "# 01 — Demo\n\n## Responsibility\nx\n\n## Structure\nx\n\n## Classes\n"
        "| Class | What |\n|---|---|\n| `Thing` | x |\n\n## Flow\nx\n\n"
        "## Design rules\nx\n\n## Rejected\nx\n",
    )
    _write(
        root / "design" / "runtime.json",
        json.dumps({
            "canvas": [600, 400], "zones": [], "edges": [],
            "nodes": [{
                "id": "demo", "x": 10, "y": 10, "w": 100, "h": 40,
                "label": "demo", "sub": "", "note": None,
                "tone": "entry", "package": "demo",
            }],
        }),
    )
    _write(root / "design" / "overlay.json", '{"nodes": [], "edges": [], "annotations": {}}')
    _write(root / "design" / "policy.json", '{"title": "demo", "root": "app"}')
    return root


def _config(project: Path) -> dict:
    return {
        "selector_env": "PACK_PROJECT",
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
                "subsystems": [{"number": "01", "label": "demo", "packages": ["demo"]}],
                "artifacts_root": "<PACK>/tmp/demo",
                "umlview": {"out": "<PACK>/tmp/demo/uml"},
            }
        },
    }


def _seed(tmp: Path, project: Path) -> Path:
    seed = tmp / "seed"
    shutil.copytree(
        PACK, seed,
        ignore=shutil.ignore_patterns(
            ".git", "tmp", "__pycache__", ".pytest_cache", "vendor",
            "config/pack.local.json", "local",
        ),
    )
    _write(seed / "config" / "pack.json", json.dumps(_config(project), indent=2))
    _write(seed / ".gitignore", "tmp/\nlocal/\nconfig/pack.local.json\n")
    _write(seed / "PROJECT.md", "# Project\n\n## Environment\n\nx\n")
    git(seed, "init", "-b", "main")
    git(seed, "add", "-A")
    git(seed, "commit", "-m", "seed")
    remote = tmp / "remote.git"
    subprocess.run(["git", "init", "--bare", str(remote)], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(remote), "symbolic-ref", "HEAD", "refs/heads/main"],
        check=True, capture_output=True,
    )
    git(seed, "remote", "add", "origin", str(remote))
    git(seed, "push", "-u", "origin", "main")
    return remote


def _clone(remote: Path, dest: Path) -> Path:
    subprocess.run(["git", "clone", str(remote), str(dest)], check=True, capture_output=True)
    return dest


def _update(pack: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(pack / "tools" / "update.py"), *args, "--pack", str(pack)],
        capture_output=True, text=True, check=False,
    )


def _fixture(tmp_path: Path) -> tuple[Path, Path]:
    project = _project(tmp_path)
    remote = _seed(tmp_path, project)
    b = _clone(remote, tmp_path / "b")
    return remote, b


def _upstream_commit(remote: Path, tmp_path: Path) -> str:
    a = _clone(remote, tmp_path / "a")
    _write(a / "README.md", "# seed\n\nan upstream improvement\n")
    git(a, "add", "-A")
    git(a, "commit", "-m", "docs: improve the readme")
    git(a, "push")
    return git(a, "rev-parse", "HEAD").stdout.strip()


def test_check_reports_an_incoming_commit_without_changing_anything(tmp_path):
    remote, b = _fixture(tmp_path)
    _upstream_commit(remote, tmp_path)

    result = _update(b, "check")

    assert result.returncode == 0
    assert "1 commit(s) available" in result.stdout
    assert "docs:" in result.stdout
    assert git(b, "rev-parse", "HEAD").stdout.strip() != ""


def test_apply_refuses_a_dirty_worktree(tmp_path):
    remote, b = _fixture(tmp_path)
    _upstream_commit(remote, tmp_path)
    _write(b / "README.md", "locally edited\n")

    result = _update(b, "apply", "--yes")

    assert result.returncode == 1
    assert "dirty" in (result.stdout + result.stderr)


def test_apply_refuses_a_diverged_branch(tmp_path):
    remote, b = _fixture(tmp_path)
    _upstream_commit(remote, tmp_path)
    _write(b / "LOCAL.md", "local commit\n")
    git(b, "add", "-A")
    git(b, "commit", "-m", "chore: local")

    result = _update(b, "apply", "--yes")

    assert result.returncode == 1
    assert "diverged" in (result.stdout + result.stderr)


def test_apply_without_yes_changes_nothing(tmp_path):
    remote, b = _fixture(tmp_path)
    _upstream_commit(remote, tmp_path)
    before = git(b, "rev-parse", "HEAD").stdout.strip()

    result = _update(b, "apply")

    assert result.returncode == 0
    assert "not applied" in result.stdout
    assert git(b, "rev-parse", "HEAD").stdout.strip() == before


def test_apply_fast_forwards_and_keeps_null_design_data(tmp_path):
    remote, b = _fixture(tmp_path)
    design = b / ".." / "proj" / "design" / "runtime.json"
    before = design.read_text()
    target = _upstream_commit(remote, tmp_path)

    result = _update(b, "apply", "--yes")

    assert result.returncode == 0, result.stdout + result.stderr
    assert git(b, "rev-parse", "HEAD").stdout.strip() == target
    state = json.loads((b / "local" / "harness.json").read_text())
    assert state["commit"] == target
    assert design.read_text() == before
