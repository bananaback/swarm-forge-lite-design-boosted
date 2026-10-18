"""Unit tests for the `swarm.uml({op:'sync'})` CRAP-report guard."""

import swarm_uml


class _Paths:
    """A PathSet stub rooted at one temporary project."""

    def __init__(self, root):
        self._root = root

    def workspace_root(self):
        return self._root

    def artifacts_root(self):
        return self._root / "dump"

    def source_roots(self):
        return (self._root / "src",)

    def persistent_roots(self):
        return ()


def _project(monkeypatch, tmp_path):
    paths = _Paths(tmp_path)
    monkeypatch.setattr(swarm_uml, "_paths", lambda: paths)
    return paths


def test_a_missing_report_stops_the_sync_before_it_runs(monkeypatch, tmp_path):
    _project(monkeypatch, tmp_path)
    ran = []
    monkeypatch.setattr(swarm_uml, "_run", lambda *a, **k: ran.append(a) or (0, "", ""))
    model = tmp_path / "model.json"

    result = swarm_uml.cmd_uml_sync({"model": str(model)})

    assert result["exit"] == 2
    assert result["ok"] is False
    assert "no CRAP report" in result["stderr"]
    assert ran == []
    assert not model.exists()


def test_the_default_report_is_used_when_crap_is_absent(monkeypatch, tmp_path):
    paths = _project(monkeypatch, tmp_path)
    report = paths.artifacts_root() / ".metrics" / "crap.txt"
    report.parent.mkdir(parents=True)
    report.write_text("Function Namespace CC Cov% CRAP\n")
    captured = {}

    def fake_run(argv, cwd=None, env=None):
        captured["argv"] = argv
        return 0, "", ""

    monkeypatch.setattr(swarm_uml, "_run", fake_run)

    result = swarm_uml.cmd_uml_sync({"model": str(tmp_path / "model.json")})

    argv = captured["argv"]
    assert argv[argv.index("--crap") + 1] == str(report)
    assert result["exit"] == 0
    assert str(report) in result["warn"]


def test_a_model_under_a_subsystem_uses_that_lane_report(monkeypatch, tmp_path):
    _project(monkeypatch, tmp_path)
    monkeypatch.setattr(swarm_uml, "PACK", tmp_path)
    model = tmp_path / "design" / "subsystems" / "foo" / "model.json"
    report = tmp_path / "dump" / "foo" / ".metrics" / "crap.txt"
    report.parent.mkdir(parents=True)
    report.write_text("Function Namespace CC Cov% CRAP\n")
    captured = {}

    def fake_run(argv, cwd=None, env=None):
        captured["argv"] = argv
        return 0, "", ""

    monkeypatch.setattr(swarm_uml, "_run", fake_run)

    swarm_uml.cmd_uml_sync({"model": str(model)})

    argv = captured["argv"]
    assert argv[argv.index("--crap") + 1] == str(report)
