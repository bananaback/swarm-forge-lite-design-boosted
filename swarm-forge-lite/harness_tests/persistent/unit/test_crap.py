"""Unit tests for the pack's crapper wrapper (`swarm_json.cmd_crap`)."""

import os
import sys

import swarm_json

REPORT = (
    "CRAP Report\n"
    "===========\n"
    "Languages: python\n"
    "\n"
    "Function                       Namespace      CC    Cov%     CRAP\n"
    "--------------------------------------------------------------\n"
    "four                           four            4    0.0%     20.0\n"
    "branched                       sample          3  100.0%      3.0\n"
    "simple                         sample          1  100.0%      1.0\n"
    "absent                         sample          2      N/A      N/A\n"
    "\n"
)


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
    monkeypatch.setattr(swarm_json, "_paths", lambda: paths)
    return paths


def _capture(monkeypatch, output=REPORT):
    captured = {}

    def fake_run(argv, cwd=None, env=None):
        captured["argv"] = argv
        captured["env"] = env
        return 0, output, "Wrote ...\n"

    monkeypatch.setattr(swarm_json, "_run", fake_run)
    return captured


def test_the_report_rows_carry_the_namespace_and_the_score():
    rows = swarm_json._crap_rows(REPORT)
    assert [row["function"] for row in rows] == [
        "four",
        "branched",
        "simple",
        "absent",
    ]
    assert rows[0] == {
        "function": "four",
        "namespace": "four",
        "cc": 4,
        "coverage": "0.0%",
        "crap": "20.0",
    }
    assert rows[3]["crap"] == "N/A"


def test_the_header_and_the_separator_are_not_rows():
    assert swarm_json._crap_rows("CRAP Report\n=======\nLanguages: python\n") == []


def test_only_the_scores_above_the_threshold_are_kept():
    rows = swarm_json._crap_rows(REPORT)
    assert [row["function"] for row in swarm_json._crap_over(rows)] == ["four"]


def test_cmd_crap_runs_the_vendored_tool_at_the_pack_threshold(monkeypatch, tmp_path):
    captured = _capture(monkeypatch)
    _project(monkeypatch, tmp_path)

    result = swarm_json.cmd_crap({"useExisting": True})

    argv = captured["argv"]
    assert argv[:3] == [sys.executable, "-m", "crapper"]
    assert argv[argv.index("--threshold") + 1] == "10"
    assert argv[argv.index("--root") + 1] == str(tmp_path / "dump")
    assert str(tmp_path / "src") in argv
    assert "--use-existing-coverage" in argv
    assert result["tool"] == "crapper"
    assert result["threshold"] == 10.0
    assert result["total"] == 4
    assert result["above"] == 1
    assert [row["function"] for row in result["rows"]] == ["four"]


def test_cmd_crap_all_returns_every_row(monkeypatch, tmp_path):
    _capture(monkeypatch)
    _project(monkeypatch, tmp_path)

    result = swarm_json.cmd_crap({"useExisting": True, "all": True})

    assert result["total"] == 4
    assert len(result["rows"]) == 4


def _write_source(root, age):
    source = root / "src" / "a.py"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text("x = 1\n")
    os.utime(source, (age, age))


def _write_report(paths, age):
    report = swarm_json._crap_report(paths.artifacts_root())
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text("")
    os.utime(report, (age, age))
    return report


def test_reuse_fresh_reuses_a_report_newer_than_the_sources(monkeypatch, tmp_path):
    paths = _project(monkeypatch, tmp_path)
    report = _write_report(paths, 2000.0)
    _write_source(tmp_path, report.stat().st_mtime - 10)
    captured = _capture(monkeypatch)

    swarm_json.cmd_crap({"reuseFresh": True})

    assert "--use-existing-coverage" in captured["argv"]
    assert "--coverage-command" not in captured["argv"]


def test_reuse_fresh_runs_the_tests_when_a_source_is_newer(monkeypatch, tmp_path):
    paths = _project(monkeypatch, tmp_path)
    report = _write_report(paths, 2000.0)
    _write_source(tmp_path, report.stat().st_mtime + 10)
    captured = _capture(monkeypatch)

    swarm_json.cmd_crap({"reuseFresh": True})

    assert "--coverage-command" in captured["argv"]
    assert "--use-existing-coverage" not in captured["argv"]


def test_the_default_run_passes_a_coverage_command(monkeypatch, tmp_path):
    captured = _capture(monkeypatch)
    _project(monkeypatch, tmp_path)

    swarm_json.cmd_crap({})

    command = captured["argv"][captured["argv"].index("--coverage-command") + 1]
    assert "-m coverage run" in command
    assert "-m pytest" in command
