"""Unit tests for the crap4py measurement, coverage, and provider helpers."""

import json
import os
from pathlib import Path
from types import SimpleNamespace

import crap4py.cli as crap_cli
import pytest
from crap4py.cli import coverage_provider
from crap4py.complexity import RadonComplexity, parse_radon_report, run_radon
from crap4py.coverage import Coverage
from crap4py.errors import ToolError
from crap4py.function import Function
from crap4py.measurement import Measurement
from crap4py.providers import CommandCoverage, ExistingCoverage, PytestCoverage


def _function(complexity: int, lineno: int = 1, endline: int = 2) -> Function:
    return Function("fn", "module.py", lineno, endline, complexity)


def test_crap_score_is_zero_coverage_squared_plus_complexity():
    function = _function(3)
    assert function.crap(0.0) == pytest.approx(12.0)
    assert function.crap(1.0) == pytest.approx(3.0)


def test_crap_score_uses_the_coverage_fraction():
    assert _function(3).crap(1 / 3) == pytest.approx(5.6667, abs=1e-3)


def test_measurement_reports_the_hit_fraction():
    measurement = Measurement(_function(3, 1, 3), {1: 1, 2: 0, 3: 0})
    assert measurement.coverage_text() == "33.3%"
    assert measurement.score_text() == "5.7"


def test_measurement_without_lines_in_range_reports_unmeasured():
    measurement = Measurement(_function(1), {})
    assert measurement.coverage_text() == "unmeasured"
    assert measurement.score_text() == "unmeasured"
    assert measurement.sort_key()[0] is True


def test_measurement_above_the_threshold_is_counted():
    assert Measurement(_function(4), {1: 0, 2: 0}).exceeds() is True
    assert Measurement(_function(10), {1: 1, 2: 1}).exceeds() is False


def test_measurement_ranks_uncovered_before_covered():
    covered = Measurement(_function(1, 1, 2), {1: 1, 2: 1})
    uncovered = Measurement(_function(1, 3, 4), {3: 0, 4: 0})
    assert sorted((covered, uncovered), key=Measurement.sort_key) == [
        uncovered,
        covered,
    ]


def test_coverage_loads_line_hits_for_an_absolute_file(tmp_path):
    module = tmp_path / "module.py"
    module.write_text("x = 1\n")
    lcov = tmp_path / "coverage.lcov"
    lcov.write_text(f"SF:{module}\nDA:1,2\nend_of_record\n")
    coverage = Coverage.load(lcov)
    assert coverage.hits_for(Function("fn", str(module), 1, 1, 1)) == {1: 2}


def test_coverage_refuses_a_data_line_before_any_source_line(tmp_path):
    lcov = tmp_path / "coverage.lcov"
    lcov.write_text("DA:1,1\n")
    with pytest.raises(ToolError, match="malformed"):
        Coverage.load(lcov)


def test_empty_coverage_has_no_hits():
    assert Coverage.empty().hits_for(_function(1)) == {}


def _args(**overrides):
    values = {
        "lcov": None,
        "use_existing_coverage": False,
        "coverage_command": None,
        "test_path": [],
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_coverage_provider_selects_existing_coverage():
    provider = coverage_provider(
        _args(use_existing_coverage=True),
        SimpleNamespace(artifacts_root=Path("/artifacts"), source_roots=()),
    )
    assert isinstance(provider, ExistingCoverage)
    assert provider.lcov == Path("/artifacts/coverage.lcov")


def test_coverage_provider_selects_a_command():
    provider = coverage_provider(
        _args(coverage_command="make coverage {lcov}"),
        SimpleNamespace(artifacts_root=Path("/artifacts"), source_roots=()),
    )
    assert isinstance(provider, CommandCoverage)
    assert provider.command == "make coverage {lcov}"


def test_coverage_provider_defaults_to_the_pytest_run():
    provider = coverage_provider(
        _args(),
        SimpleNamespace(artifacts_root=Path("/artifacts"), source_roots=()),
    )
    assert isinstance(provider, PytestCoverage)
    assert provider.artifacts == Path("/artifacts")


def test_parse_radon_report_keeps_functions_and_methods():
    raw = json.dumps(
        {
            "src/sample.py": [
                {
                    "type": "function",
                    "name": "simple",
                    "lineno": 1,
                    "endline": 2,
                    "complexity": 1,
                },
                {
                    "type": "method",
                    "name": "Widget.run",
                    "lineno": 5,
                    "endline": 9,
                    "complexity": 3,
                },
                {
                    "type": "class",
                    "name": "Widget",
                    "lineno": 4,
                    "endline": 9,
                    "complexity": 2,
                },
            ],
            "src/empty.py": [],
            "src/other.py": "not-a-list",
        }
    )
    functions = parse_radon_report(raw)
    assert [
        (f.name, f.path, f.lineno, f.endline, f.complexity) for f in functions
    ] == [
        ("simple", os.path.normpath("src/sample.py"), 1, 2, 1),
        ("Widget.run", os.path.normpath("src/sample.py"), 5, 9, 3),
    ]


def test_parse_radon_report_refuses_invalid_json():
    with pytest.raises(ToolError, match="cannot parse radon output"):
        parse_radon_report("not json")


def test_run_radon_returns_the_process_stdout(monkeypatch):
    class Completed:
        returncode = 0
        stdout = '{"a.py": []}'
        stderr = ""

    def fake_run(argv, **kwargs):
        assert "radon" in argv
        return Completed()

    monkeypatch.setattr("crap4py.complexity.subprocess.run", fake_run)
    assert run_radon(("src",)) == '{"a.py": []}'


def test_run_radon_reports_a_failure(monkeypatch):
    class Completed:
        returncode = 9
        stdout = ""
        stderr = "radon exploded\n"

    monkeypatch.setattr(
        "crap4py.complexity.subprocess.run", lambda argv, **kwargs: Completed()
    )
    with pytest.raises(ToolError, match="radon failed: radon exploded"):
        run_radon(("src",))


def test_radon_complexity_parses_the_run_output(monkeypatch):
    monkeypatch.setattr(
        "crap4py.complexity.run_radon",
        lambda roots: json.dumps(
            {
                "m.py": [
                    {
                        "type": "function",
                        "name": "fn",
                        "lineno": 1,
                        "endline": 2,
                        "complexity": 4,
                    }
                ]
            }
        ),
    )
    functions = RadonComplexity(("src",)).functions()
    assert [f.name for f in functions] == ["fn"]
    assert functions[0].complexity == 4


def _resolved(**overrides):
    values = {"artifacts_root": Path("/artifacts"), "source_roots": ()}
    values.update(overrides)
    return SimpleNamespace(**values)


@pytest.mark.parametrize(
    "argv, expected",
    [
        (["--source-root", "/given", "--use-existing-coverage"], ("/given",)),
        ([], ("/wired",)),
    ],
)
def test_main_selects_the_source_roots(monkeypatch, argv, expected):
    monkeypatch.setattr(
        crap_cli.wiring, "load", lambda: _resolved(source_roots=(Path("/wired"),))
    )
    captured = {}

    def fake_run(self):
        captured["roots"] = self._complexity._roots
        return 0

    monkeypatch.setattr(crap_cli.CrapTool, "run", fake_run)
    assert crap_cli.main(argv) == 0
    assert captured["roots"] == expected


def test_main_prints_a_tool_error(monkeypatch, capsys):
    monkeypatch.setattr(crap_cli.wiring, "load", lambda: _resolved())

    def boom(self):
        raise ToolError("kaboom")

    monkeypatch.setattr(crap_cli.CrapTool, "run", boom)
    assert crap_cli.main([]) == 1
    assert "crap4py: kaboom" in capsys.readouterr().err
