"""The gherkin-parser wrapper must work from any working directory."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
WRAPPER = HERE / "gherkin-parser"
FEATURE = """\
Feature: wrapper cwd
  Scenario: parse from a cwd that holds the wrapper
    Given a feature file
    Then the parser writes one IR
"""

pytestmark = pytest.mark.skipif(shutil.which("bb") is None, reason="bb is not on PATH")


@pytest.mark.parametrize("cwd", ["shared", "tmp"])
def test_wrapper_parses_from_any_working_directory(tmp_path, cwd):
    feature = tmp_path / "sample.feature"
    feature.write_text(FEATURE, encoding="utf-8")
    output = tmp_path / "sample.json"
    working_dir = HERE if cwd == "shared" else tmp_path
    result = subprocess.run(
        [str(WRAPPER), str(feature), str(output)],
        cwd=working_dir,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert output.is_file()
