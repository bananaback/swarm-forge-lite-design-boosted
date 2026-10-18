"""Unit tests for the shared claim board and the deferred goal queue."""

from datetime import UTC, datetime
from pathlib import Path

import task_board

NOW = datetime(2026, 10, 18, 8, 0, tzinfo=UTC)

BOARD = """# TASK BOARD

Updated: 2026-10-18T08:00:00Z
Stale after: 60 minutes

| Claim | Session | Role | Subsystem | Task | Files | State | Since |
|---|---|---|---|---|---|---|---|
| C1 | ses_a | orchestrator | audio-output | implement clip gate | app/audio/**, tests/audio/** | active | 2026-10-18T07:30:00Z |
| C2 | ses_b | orchestrator | detection-extraction | add filter | app/detect/** | active | 2026-10-18T05:00:00Z |
| C3 | ses_c | orchestrator | audio-output | old task | app/audio/x.py | done | 2026-10-18T06:00:00Z |
"""

TODO = """# TODO

| Id | Goal | Subsystem | Ready | Done when | Notes |
|---|---|---|---|---|---|
| T1 | add cross-session board | harness | no | two sessions see one claim | wait for T2 |
| T2 | add deferred queue | harness | yes | pick T2 works | owner |
| T3 | later | harness | yes | - | - |
"""


def _write(tmp_path: Path, name: str, text: str) -> Path:
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


def test_reads_the_header_and_every_claim(tmp_path):
    board = task_board.read_board(_write(tmp_path, "TASK_BOARD.md", BOARD))
    assert board.updated == "2026-10-18T08:00:00Z"
    assert board.stale_minutes == 60
    assert [claim.id for claim in board.claims] == ["C1", "C2", "C3"]
    assert board.claims[0].files == ("app/audio/**", "tests/audio/**")


def test_a_missing_board_is_empty(tmp_path):
    board = task_board.read_board(tmp_path / "missing.md")
    assert board.claims == ()
    assert board.stale_minutes == 60


def test_overlap_is_conservative():
    assert task_board.overlaps("app/**", "app/audio/x.py")
    assert task_board.overlaps("app/audio/**", "app/audio/x.py")
    assert not task_board.overlaps("app/audio/**", "tests/**")
    assert task_board.overlaps("*", "tests/audio/x.py")
    assert task_board.overlaps("tests/audio/**", "tests/audio/**")


def test_a_conflict_is_another_sessions_active_claim_on_the_same_area(tmp_path):
    board = task_board.read_board(_write(tmp_path, "TASK_BOARD.md", BOARD))
    claims = task_board.conflicts(
        board, "ses_new", "audio-output", ("app/audio/player.py",)
    )
    assert [claim.id for claim in claims] == ["C1"]

    claims = task_board.conflicts(board, "ses_new", "", ("app/detect/**",))
    assert [claim.id for claim in claims] == ["C2"]


def test_other_sessions_marks_a_stale_claim(tmp_path):
    board = task_board.read_board(_write(tmp_path, "TASK_BOARD.md", BOARD))
    claims = task_board.conflicts(board, "ses_new", "", ("app/detect/**",))
    text = task_board.render_other(claims, NOW, board.stale_minutes)
    assert "#OTHER SESSIONS" in text
    assert "C2" in text and "stale" in text
    assert "C1" not in text

    empty = task_board.render_other([], NOW)
    assert empty == "#OTHER SESSIONS\n- none"


def test_todo_picks_the_named_row_or_the_top_ready_row(tmp_path):
    todos = task_board.read_todo(_write(tmp_path, "TODO.md", TODO))
    assert [todo.id for todo in todos] == ["T1", "T2", "T3"]
    assert task_board.pick_todo(todos).id == "T2"
    assert task_board.pick_todo(todos, "T3").id == "T3"
    assert task_board.pick_todo(todos, "missing") is None


def test_a_missing_todo_file_is_empty(tmp_path):
    assert task_board.read_todo(tmp_path / "missing.md") == ()
