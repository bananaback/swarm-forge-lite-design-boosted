"""Unit tests for the shared OpenCode database reader and the report."""

import sqlite3

import opencode_db
import pytest
import swarm_gate


def _v2(path, columns: str, rows: list[tuple]) -> None:
    connection = sqlite3.connect(str(path))
    connection.execute(f"create table session_v2 ({columns})")
    marks = ",".join("?" for _ in rows[0])
    connection.executemany(f"insert into session_v2 values ({marks})", rows)
    connection.commit()
    connection.close()


def test_reads_only_the_columns_the_table_declares(tmp_path):
    """A database that predates an optional column still reads."""
    path = tmp_path / "opencode.db"
    _v2(
        path,
        "id text, agent text, tokens_output integer, time_created integer, time_updated integer",
        [("s1", "coder", 10, 0, 60000)],
    )
    connection = opencode_db.connect(str(path))
    rows = opencode_db.session_rows(connection)
    connection.close()
    assert rows == [
        {
            "id": "s1",
            "agent": "coder",
            "tokens_output": 10,
            "time_created": 0,
            "time_updated": 60000,
        }
    ]
    assert "tokens_reasoning" not in rows[0]


def test_prefers_session_v2_and_falls_back_to_session(tmp_path):
    """The newer table wins; an older database still reads its `session` table."""
    path = tmp_path / "opencode.db"
    _v2(path, "id text, agent text", [("new", "critic")])
    connection = opencode_db.connect(str(path))
    assert opencode_db.session_table(connection) == "session_v2"
    connection.close()

    old = tmp_path / "old.db"
    connection = sqlite3.connect(str(old))
    connection.execute("create table session (id text, agent text)")
    connection.execute("insert into session values ('old', 'designer')")
    connection.commit()
    connection.close()
    connection = opencode_db.connect(str(old))
    assert opencode_db.session_table(connection) == "session"
    assert opencode_db.session_rows(connection) == [{"id": "old", "agent": "designer"}]
    connection.close()


def test_the_database_is_opened_read_only(tmp_path):
    path = tmp_path / "opencode.db"
    _v2(path, "id text, agent text", [("s1", "coder")])
    connection = opencode_db.connect(str(path))
    with pytest.raises(sqlite3.OperationalError):
        connection.execute("delete from session_v2")
    connection.close()


def test_a_missing_database_is_an_error(tmp_path):
    with pytest.raises(FileNotFoundError, match="no OpenCode database"):
        opencode_db.connect(str(tmp_path / "missing.db"))


def test_report_aggregates_the_rows(tmp_path):
    path = tmp_path / "opencode.db"
    _v2(
        path,
        "id text, agent text, tokens_output integer, tokens_reasoning integer, "
        "time_created integer, time_updated integer",
        [
            ("s1", "coder", 10, 20, 0, 60000),
            ("s2", "coder", 5, 5, 0, 30000),
            ("s3", "critic", 7, 0, 0, 120000),
        ],
    )
    report = swarm_gate.cmd_report({"db": str(path)})
    assert report["roles"]["coder"] == {
        "out": 15,
        "reason": 25,
        "sessions": 2,
        "minutes": 1.5,
    }
    assert report["roles"]["critic"]["sessions"] == 1
