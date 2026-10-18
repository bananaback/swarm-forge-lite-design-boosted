#!/usr/bin/env python3
"""opencode_db -- read the OpenCode session database, read-only.

One reader for the Python tools. `convo` is a Bun plugin and keeps its own
reader; it cannot import this module without a process boundary. Both follow the
same table order (`session_v2` then `session`) and tolerate a missing optional
column.
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

DEFAULT_DB = Path.home() / ".local" / "share" / "opencode" / "opencode.db"

V2_TABLE = "session_v2"

V1_TABLE = "session"

# The fields `swarm.report` needs, plus the identity of a row. A table that
# predates one of them is still readable: the missing field is absent.
SESSION_FIELDS = (
    "id",
    "agent",
    "cost",
    "tokens_input",
    "tokens_output",
    "tokens_reasoning",
    "time_created",
    "time_updated",
)


def db_path(raw: str | None = None) -> Path:
    """The database file: an explicit path, then OPENCODE_DB, then the default."""
    return Path(raw or os.environ.get("OPENCODE_DB") or DEFAULT_DB).expanduser()


def connect(raw: str | None = None) -> sqlite3.Connection:
    """Open the database read-only. A missing file is an error, never a new DB."""
    path = db_path(raw)
    if not path.is_file():
        raise FileNotFoundError(f"no OpenCode database at {path}")
    return sqlite3.connect(f"file:{path}?mode=ro", uri=True)


def has_table(connection: sqlite3.Connection, name: str) -> bool:
    row = connection.execute(
        "select 1 from sqlite_master where type='table' and name=?", (name,)
    ).fetchone()
    return row is not None


def session_table(connection: sqlite3.Connection) -> str | None:
    """The storage generation to read: v2 when present, else v1."""
    for name in (V2_TABLE, V1_TABLE):
        if has_table(connection, name):
            return name
    return None


def columns(connection: sqlite3.Connection, table: str) -> set[str]:
    return {str(row[1]) for row in connection.execute(f"PRAGMA table_info({table})")}


def session_rows(connection: sqlite3.Connection) -> list[dict]:
    """Every session row as a dict, with only the fields the table declares."""
    table = session_table(connection)
    if table is None:
        return []
    declared = columns(connection, table)
    fields = [field for field in SESSION_FIELDS if field in declared]
    if not fields:
        return []
    rows = connection.execute(f"select {','.join(fields)} from {table}").fetchall()
    return [dict(zip(fields, row)) for row in rows]
