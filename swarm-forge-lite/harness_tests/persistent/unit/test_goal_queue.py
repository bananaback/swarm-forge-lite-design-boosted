"""Unit tests for the deferred goal queue."""

from pathlib import Path

import goal_queue

TODO = """# TODO

| Id | Goal | Subsystem | Ready | Done when | Notes |
|---|---|---|---|---|---|
| T1 | add cross-session board | harness | no | two sessions see one claim | wait for T2 |
| T2 | add deferred queue | harness | yes | pick T2 works | owner |
| T3 | later | harness | yes | - | - |
"""


def _write(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "TODO.md"
    path.write_text(text, encoding="utf-8")
    return path


def test_picks_the_named_row_or_the_top_ready_row(tmp_path):
    todos = goal_queue.read_todo(_write(tmp_path, TODO))
    assert [todo.id for todo in todos] == ["T1", "T2", "T3"]
    assert goal_queue.pick_todo(todos).id == "T2"
    assert goal_queue.pick_todo(todos, "T3").id == "T3"
    assert goal_queue.pick_todo(todos, "missing") is None


def test_a_missing_file_is_an_empty_queue(tmp_path):
    assert goal_queue.read_todo(tmp_path / "missing.md") == ()
