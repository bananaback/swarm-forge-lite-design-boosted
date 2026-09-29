"""Unit tests for wiring path resolution and the harness CLI value objects."""

import json
from pathlib import Path

import harness
import pytest
import wiring
from harness import (
    CleanTarget,
    ClearReport,
    HarnessError,
    OptionalRoot,
    PathStatus,
    PersistentRoot,
    status_report,
)


class FakePaths:
    def pack_root(self):
        return Path("/pack")

    def config_path(self):
        return Path("/pack/harness.json")

    def workspace_root(self):
        return Path("/work")

    def state_root(self):
        return Path("/state")

    def artifacts_root(self):
        return Path("/artifacts")

    def hot_tests(self):
        return Path("/hot")

    def features(self):
        return OptionalRoot.of(Path("/features"))

    def specs(self):
        return OptionalRoot.of(Path("/specs"))

    def source_roots(self):
        return (Path("/src"),)

    def persistent_roots(self):
        return (PersistentRoot(Path("/tests"), "harness"),)

    def as_dict(self):
        return {}


class FakeTree:
    def __init__(self, present):
        self._present = set(present)

    def exists(self, path):
        return path in self._present

    def count_entries(self, path):
        return 0

    def clear(self, path):
        pass


def _write_config(tmp_path, **fields):
    document = {
        "workspace_root": ".",
        "state_root": "state",
        "artifacts_root": "artifacts",
        "hot_tests": "hot",
        "source_roots": ["src"],
        "features": "features",
        **fields,
    }
    config = tmp_path / "harness.json"
    config.write_text(json.dumps(document))
    return config


def test_optional_root_absence_is_a_value():
    absent = OptionalRoot.of(None)
    assert not absent.is_configured()
    assert absent.text() == "(none)"
    with pytest.raises(HarnessError, match="no root"):
        absent.require()
    present = OptionalRoot.of(Path("/x"))
    assert present.is_configured()
    assert present.require() == Path("/x")
    assert present.text() == "/x"


def test_path_status_renders_presence():
    present = PathStatus("PACK", "/pack", True).render()
    assert present.startswith("PACK")
    assert "[ok]" in present
    absent = PathStatus("HOT", "/hot", False).render()
    assert "[-]" in absent


def test_clear_report_counts_entries():
    assert ClearReport("hot", Path("/h"), 1).render() == "CLEANED hot: /h (1 entry)"
    assert ClearReport("hot", Path("/h"), 3).render() == "CLEANED hot: /h (3 entries)"


def test_clean_target_refuses_an_unknown_name():
    with pytest.raises(HarnessError, match="unknown clean target"):
        CleanTarget.parse("bogus")


def test_clean_target_all_names_hot_artifacts_and_state():
    labels = [label for label, _ in CleanTarget.parse("all").roots(FakePaths())]
    assert labels == ["hot", "artifacts", "state"]


def test_status_report_has_a_row_per_resolved_path():
    report = status_report(FakePaths(), FakeTree({Path("/pack"), Path("/src")}))
    rendered = [row.render() for row in report.rows]
    labels = [row.label for row in report.rows]
    assert labels == [
        "PACK",
        "CONFIG",
        "WORKSPACE",
        "STATE",
        "ARTIFACTS",
        "HOT",
        "FEATURES",
        "SPECS",
        "SOURCE",
        "PERSIST",
    ]
    assert "[ok]" in rendered[0]
    assert "[-]" in rendered[1]
    assert "[ok]" in rendered[8]


def test_wiring_resolves_every_path_against_the_config_directory(tmp_path):
    config = _write_config(
        tmp_path,
        persistent_tests=[{"root": "unit", "kind": "harness"}],
    )
    resolved = wiring.load(config=str(config))
    assert resolved.workspace_root == tmp_path.resolve()
    assert resolved.state_root == (tmp_path / "state").resolve()
    assert resolved.artifacts_root == (tmp_path / "artifacts").resolve()
    assert resolved.hot_tests == (tmp_path / "hot").resolve()
    assert resolved.features == (tmp_path / "features").resolve()
    assert resolved.source_roots == ((tmp_path / "src").resolve(),)
    assert resolved.persistent_tests[0]["root"] == (tmp_path / "unit").resolve()
    assert resolved.config_path == config.resolve()
    assert resolved.as_dict()["workspace_root"] == str(tmp_path.resolve())


def test_swarm_lane_scopes_the_disposable_roots(tmp_path):
    config = _write_config(
        tmp_path,
        persistent_tests=[{"root": "unit", "kind": "harness"}],
    )
    resolved = wiring.load(config=str(config), environ={"SWARM_LANE": "lane-a"})
    assert resolved.workspace_root == tmp_path.resolve()
    assert resolved.state_root == (tmp_path / "state" / "lane-a").resolve()
    assert resolved.artifacts_root == (tmp_path / "artifacts" / "lane-a").resolve()
    assert resolved.hot_tests == (tmp_path / "hot" / "lane-a").resolve()


def test_swarm_lane_must_be_one_path_segment(tmp_path):
    config = _write_config(tmp_path)
    with pytest.raises(wiring.WiringError):
        wiring.load(config=str(config), environ={"SWARM_LANE": "../escape"})


def test_wiring_reports_an_unconfigured_features_root(tmp_path):
    document = {
        "workspace_root": ".",
        "state_root": "state",
        "artifacts_root": "artifacts",
        "hot_tests": "hot",
        "source_roots": ["src"],
    }
    config = tmp_path / "harness.json"
    config.write_text(json.dumps(document))
    assert wiring.load(config=str(config)).features is None


def test_wiring_resolves_specs_against_the_config_directory(tmp_path):
    config = _write_config(
        tmp_path,
        specs="specs",
        persistent_tests=[{"root": "unit", "kind": "harness"}],
    )
    assert wiring.load(config=str(config)).specs == (tmp_path / "specs").resolve()


def test_status_row_marks_an_absent_specs_root(tmp_path):
    document = {
        "workspace_root": ".",
        "state_root": "state",
        "artifacts_root": "artifacts",
        "hot_tests": "hot",
        "source_roots": ["src"],
    }
    config = tmp_path / "harness.json"
    config.write_text(json.dumps(document))
    paths = harness.load_path_set(str(config))
    row = next(
        entry for entry in status_report(paths, FakeTree(set())).rows
        if entry.label == "SPECS"
    )
    assert row.text == "(none)"
    assert "[-]" in row.render()


def test_status_row_marks_a_present_specs_root(tmp_path):
    config = _write_config(
        tmp_path,
        specs="specs",
        persistent_tests=[{"root": "unit", "kind": "harness"}],
    )
    target = (tmp_path / "specs").resolve()
    target.mkdir()
    paths = harness.load_path_set(str(config))
    row = next(
        entry for entry in status_report(paths, FakeTree({target})).rows
        if entry.label == "SPECS"
    )
    assert row.text == str(target)
    assert "[ok]" in row.render()


def test_resolve_pack_root_prefers_swarm_pack(tmp_path):
    assert wiring.resolve_pack_root({}) == wiring.PACK_ROOT
    assert wiring.resolve_pack_root({"SWARM_PACK": str(tmp_path)}) == tmp_path.resolve()


def test_swarm_pack_overrides_the_pack_root(tmp_path, monkeypatch):
    other = tmp_path / "other-pack"
    other.mkdir()
    config = _write_config(tmp_path)
    monkeypatch.setenv("SWARM_PACK", str(other))
    assert wiring.load(config=str(config)).pack_root == other.resolve()


def test_load_path_set_refuses_a_missing_config(tmp_path):
    with pytest.raises(HarnessError, match="missing.json"):
        harness.load_path_set(str(tmp_path / "missing.json"))


def test_main_status_reports_the_pack_row(tmp_path, capsys):
    config = _write_config(tmp_path)
    assert harness.main(["--config", str(config), "status"]) == 0
    assert "PACK" in capsys.readouterr().out


def test_main_clean_empties_the_hot_area(tmp_path, capsys):
    config = _write_config(tmp_path)
    hot = tmp_path / "hot"
    hot.mkdir()
    (hot / "a.txt").write_text("x")
    (hot / "b.txt").write_text("y")
    assert harness.main(["--config", str(config), "clean", "hot"]) == 0
    assert "(2 entries)" in capsys.readouterr().out
    assert list(hot.iterdir()) == []


def test_main_refuses_a_missing_config(tmp_path, capsys):
    code = harness.main(["--config", str(tmp_path / "missing.json"), "status"])
    assert code == 2
    assert "missing.json" in capsys.readouterr().err


def test_main_refuses_an_unknown_clean_target(tmp_path):
    config = _write_config(tmp_path)
    with pytest.raises(SystemExit) as error:
        harness.main(["--config", str(config), "clean", "bogus"])
    assert error.value.code == 2
