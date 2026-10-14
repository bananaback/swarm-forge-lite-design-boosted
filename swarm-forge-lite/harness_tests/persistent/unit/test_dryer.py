"""Unit tests for the pack's dryer wrapper (`swarm_json.cmd_dry`)."""

import sys

import swarm_json

REPORT = (
    "DUPLICATE score=0.89\n"
    "  /pkg/src/billing/invoice.py:3-13\n"
    "  /pkg/src/billing/receipt.py:3-14\n"
    "\n"
    "DUPLICATE score=0.83\n"
    "  /pkg/src/ui/view.py:1-6\n"
    "  /pkg/src/ui/panel.py:1-6\n"
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
        return 0, output, "Wrote .../dry.edn\n"

    monkeypatch.setattr(swarm_json, "_run", fake_run)
    return captured


def test_the_pairs_carry_both_positions():
    assert swarm_json._dry_pairs(REPORT) == [
        ["/pkg/src/billing/invoice.py:3-13", "/pkg/src/billing/receipt.py:3-14"],
        ["/pkg/src/ui/view.py:1-6", "/pkg/src/ui/panel.py:1-6"],
    ]


def test_a_clean_report_has_no_pairs():
    assert swarm_json._dry_pairs("No duplicate candidates found.\n") == []


def test_the_score_line_is_not_a_position():
    assert swarm_json._dry_pairs("DUPLICATE score=0.9\n") == []


def test_cmd_dry_runs_the_vendored_tool_at_the_defaults(monkeypatch, tmp_path):
    captured = _capture(monkeypatch)
    _project(monkeypatch, tmp_path)

    result = swarm_json.cmd_dry({"view": "rows"})

    argv = captured["argv"]
    assert argv[:3] == [sys.executable, "-m", "dryer"]
    assert argv[argv.index("--root") + 1] == str(tmp_path / "dump")
    assert argv[argv.index("--min-lines") + 1] == "4"
    assert argv[argv.index("--min-nodes") + 1] == "20"
    assert argv[argv.index("--threshold") + 1] == "0.82"
    assert str(tmp_path / "src") in argv
    assert str(swarm_json.PACK / "tools" / "shared") in captured["env"]["PYTHONPATH"]
    assert result["tool"] == "dryer"
    assert result["total"] == 2
    assert result["pairs"] == [
        ["/pkg/src/billing/invoice.py:3-13", "/pkg/src/billing/receipt.py:3-14"],
        ["/pkg/src/ui/view.py:1-6", "/pkg/src/ui/panel.py:1-6"],
    ]


def test_cmd_dry_passes_the_caller_thresholds(monkeypatch, tmp_path):
    captured = _capture(monkeypatch)
    _project(monkeypatch, tmp_path)

    swarm_json.cmd_dry({"minLines": 6, "minNodes": 40, "threshold": 0.9})

    argv = captured["argv"]
    assert argv[argv.index("--min-lines") + 1] == "6"
    assert argv[argv.index("--min-nodes") + 1] == "40"
    assert argv[argv.index("--threshold") + 1] == "0.9"


def test_cmd_dry_summary_hides_the_pairs(monkeypatch, tmp_path):
    _capture(monkeypatch)
    _project(monkeypatch, tmp_path)

    result = swarm_json.cmd_dry({})

    assert result["total"] == 2
    assert "pairs" not in result
