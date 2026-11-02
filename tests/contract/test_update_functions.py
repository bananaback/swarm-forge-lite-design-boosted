"""`update.py` in-process: check, report, migrations, apply, trial guards."""

from __future__ import annotations

import importlib.util
import json
import subprocess
from pathlib import Path

PACK = Path(__file__).resolve().parents[2]


def _update():
    spec = importlib.util.spec_from_file_location("update", PACK / "tools" / "update.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _git(cwd: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [
            "git", "-C", str(cwd),
            "-c", "user.name=test", "-c", "user.email=test@example.com",
            "-c", "commit.gpgsign=false",
            *args,
        ],
        capture_output=True, text=True, check=False,
    )


def _repo(tmp_path: Path) -> tuple[Path, Path]:
    seed = tmp_path / "seed"
    (seed / "docs").mkdir(parents=True)
    (seed / "VERSION").write_text("0.1.0\n", encoding="utf-8")
    (seed / "config").mkdir()
    (seed / "config" / "pack.json").write_text(json.dumps({"projects": {}}), encoding="utf-8")
    _git(seed, "init", "-b", "main")
    _git(seed, "add", "-A")
    _git(seed, "commit", "-m", "seed")
    remote = tmp_path / "remote.git"
    subprocess.run(["git", "init", "--bare", str(remote)], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(remote), "symbolic-ref", "HEAD", "refs/heads/main"],
        check=True, capture_output=True,
    )
    _git(seed, "remote", "add", "origin", str(remote))
    _git(seed, "push", "-u", "origin", "main")
    clone = tmp_path / "clone"
    subprocess.run(["git", "clone", str(remote), str(clone)], check=True, capture_output=True)
    return remote, clone


def _advance(remote: Path, tmp_path: Path) -> None:
    other = tmp_path / "other"
    subprocess.run(["git", "clone", str(remote), str(other)], check=True, capture_output=True)
    (other / "docs").mkdir(parents=True, exist_ok=True)
    (other / "docs" / "note.md").write_text("improvement\n", encoding="utf-8")
    _git(other, "add", "-A")
    _git(other, "commit", "-m", "docs: improvement")
    _git(other, "push")


def test_check_reports_an_error_outside_a_checkout(tmp_path):
    update = _update()

    result = update.check(tmp_path)

    assert result["error"] == "not a git checkout"


def test_check_lists_commits_and_classifies_files(tmp_path):
    update = _update()
    remote, clone = _repo(tmp_path)
    _advance(remote, tmp_path)

    result = update.check(clone)
    text = update.report(result)

    assert result["commits"]
    assert any(file["path"].endswith("docs/note.md") for file in result["files"])
    assert "docs:" in text


def test_report_refuses_a_dirty_tree(tmp_path):
    update = _update()
    result = {"error": "", "commits": [], "files": [], "dirty": ["README.md"], "diverged": False}

    text = update.report(result)

    assert "upstream them first" in text


def test_run_migrations_applies_a_new_migration_once(tmp_path):
    update = _update()
    migrations = tmp_path / "migrations"
    migrations.mkdir()
    marker = tmp_path / "marker"
    (migrations / "0001_test.py").write_text(
        "from pathlib import Path\n\n"
        "def is_needed(pack, config):\n    return True\n\n"
        "def apply(pack, config):\n"
        f"    (Path(pack) / 'marker').write_text('ran')\n",
        encoding="utf-8",
    )

    first = update.run_migrations(tmp_path, {})
    second = update.run_migrations(tmp_path, {})

    assert first == ["0001_test"]
    assert second == []
    assert marker.is_file()


def test_apply_without_yes_changes_nothing(tmp_path, capsys):
    update = _update()
    remote, clone = _repo(tmp_path)
    _advance(remote, tmp_path)
    before = _git(clone, "rev-parse", "HEAD").stdout.strip()

    assert update.apply(clone, {"projects": {}}, yes=False) == 0
    assert "not applied" in capsys.readouterr().out
    assert _git(clone, "rev-parse", "HEAD").stdout.strip() == before


def test_apply_fast_forwards_and_records_state(tmp_path):
    update = _update()
    remote, clone = _repo(tmp_path)
    _advance(remote, tmp_path)
    target = _git(remote, "rev-parse", "main").stdout.strip()

    assert update.apply(clone, {"projects": {}}, yes=True) == 0
    assert _git(clone, "rev-parse", "HEAD").stdout.strip() == target
    assert update.read_state(clone)["commit"] == target


def test_trial_without_an_upstream_is_refused(tmp_path):
    update = _update()
    (tmp_path / ".git").mkdir()

    try:
        update.trial(tmp_path)
    except RuntimeError as error:
        assert "upstream" in str(error) or "not a git" in str(error)
    else:
        raise AssertionError("trial accepted a repository with no upstream")


def test_trial_runs_and_cleans_up(tmp_path):
    update = _update()
    remote, clone = _repo(tmp_path)
    _advance(remote, tmp_path)

    rows = update.trial(clone)

    assert rows == []  # the fixture config declares no projects
    assert not (clone / "local" / "trial").exists()


def test_main_check_trial_and_apply(tmp_path, monkeypatch, capsys):
    update = _update()
    remote, clone = _repo(tmp_path)
    _advance(remote, tmp_path)
    monkeypatch.setattr(update, "PACK", clone)

    assert update.main(["check"]) == 0
    assert "commit(s) available" in capsys.readouterr().out
    assert update.main(["trial"]) == 0
    assert update.main(["apply"]) == 0
    assert "not applied" in capsys.readouterr().out
    assert update.main(["apply", "--yes"]) == 0
    assert update.read_state(clone)["commit"]
