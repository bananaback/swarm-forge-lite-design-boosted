"""Unit tests for the one-command pack sync."""

from pathlib import Path

import pytest
import sync_pack


def _pack(root: Path) -> Path:
    pack = root / "swarm-forge-lite"
    (pack / "tools" / "shared").mkdir(parents=True)
    return pack


def test_only_pack_owned_files_travel(tmp_path):
    ship = tmp_path / "ship"
    target = tmp_path / "target"
    source_pack = _pack(ship)
    target_pack = _pack(target)
    (source_pack / "tools" / "shared" / "a.py").write_text("new")
    (target_pack / "tools" / "shared" / "a.py").write_text("old")
    (source_pack / "harness.json").write_text("{}")
    (source_pack / "design" / "subsystems" / "x").mkdir(parents=True)
    (source_pack / "design" / "subsystems" / "x" / "requirements.md").write_text("x")
    (ship / "INSTALL.md").write_text("install")

    rows, extra = sync_pack.changes(ship, target)
    names = {source.relative_to(ship).as_posix() for _action, source in rows}
    assert names == {"swarm-forge-lite/tools/shared/a.py", "INSTALL.md"}
    assert not any("harness.json" in name for name in names)
    assert not any("design/subsystems" in name for name in names)
    assert extra == []


def test_apply_copies_and_never_deletes(tmp_path):
    ship = tmp_path / "ship"
    target = tmp_path / "target"
    source_pack = _pack(ship)
    target_pack = _pack(target)
    (source_pack / "protocol").mkdir()
    (source_pack / "protocol" / "README.md").write_text("new")
    (target_pack / "protocol").mkdir()
    (target_pack / "protocol" / "README.md").write_text("old")
    (target_pack / "protocol" / "local.md").write_text("local")

    rows, _extra = sync_pack.changes(ship, target)
    sync_pack.apply_changes(ship, target, rows)
    assert (target_pack / "protocol" / "README.md").read_text() == "new"
    assert (target_pack / "protocol" / "local.md").read_text() == "local"


def test_a_file_only_in_the_target_is_reported(tmp_path):
    ship = tmp_path / "ship"
    target = tmp_path / "target"
    _pack(ship)
    target_pack = _pack(target)
    (target_pack / "protocol").mkdir()
    (target_pack / "protocol" / "local.md").write_text("local")

    rows, extra = sync_pack.changes(ship, target)
    assert rows == []
    assert [path.name for path in extra] == ["local.md"]


def test_the_clone_root_is_required(tmp_path):
    with pytest.raises(SystemExit, match="does not contain"):
        sync_pack.main(["--to", str(tmp_path)])
