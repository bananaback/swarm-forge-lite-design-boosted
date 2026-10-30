"""Behavior tests for dryer's threshold gate. Run from the pack root."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

pytest.importorskip("tree_sitter_language_pack")

from dryer import cli  # noqa: E402

DUPLICATE = """\
def alpha(value):
    total = 0
    for item in value:
        total += item * 2
    return total
"""

OTHER = """\
class Other:
    def beta(self, item):
        return item + 7
"""


def _run(root: Path, threshold: str) -> int:
    return cli.run([
        "--root", str(root),
        "--source-root", str(root),
        "--threshold", threshold,
        "--min-lines", "2",
        "--min-nodes", "2",
    ])


def test_exits_2_when_a_pair_meets_the_threshold(tmp_path, capsys):
    (tmp_path / "a.py").write_text(DUPLICATE, encoding="utf-8")
    (tmp_path / "b.py").write_text(DUPLICATE, encoding="utf-8")
    assert _run(tmp_path, "0.80") == 2
    out = capsys.readouterr().out
    assert "DUPLICATE score=1.00" in out
    assert (tmp_path / ".metrics" / "dry.edn").is_file()


def test_exits_0_when_no_pair_meets_the_threshold(tmp_path, capsys):
    (tmp_path / "a.py").write_text(DUPLICATE, encoding="utf-8")
    (tmp_path / "b.py").write_text(OTHER, encoding="utf-8")
    assert _run(tmp_path, "0.80") == 0
    assert "No duplicate candidates found." in capsys.readouterr().out


def test_exits_0_when_the_threshold_is_above_every_score(tmp_path):
    (tmp_path / "a.py").write_text(DUPLICATE, encoding="utf-8")
    (tmp_path / "b.py").write_text(DUPLICATE, encoding="utf-8")
    assert _run(tmp_path, "1.01") == 0
