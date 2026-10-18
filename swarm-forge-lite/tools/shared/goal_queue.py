"""goal_queue -- read the operator-owned deferred goal queue.

`harness.py todo` calls these functions. The queue is a pointer to work, not a
second requirement record. Only an explicit operator phrase starts a row.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import record

READY_WORDS = {"yes", "y", "true", "1", "ready"}


@dataclass(frozen=True)
class Todo:
    """One row of `design/TODO.md`."""

    id: str
    goal: str
    subsystem: str
    ready: str
    done_when: str
    notes: str

    def is_ready(self) -> bool:
        return self.ready.strip().lower() in READY_WORDS


def read_todo(path: Path) -> tuple[Todo, ...]:
    """Parse the deferred goal queue. A missing file is an empty queue."""
    path = Path(path)
    if not path.is_file():
        return ()
    document = record.Document.read(path)
    table = document.table_with("id", "goal")
    if table is None:
        return ()
    rows: list[Todo] = []
    for row, _line in table.rows_with_lines():
        if record._blank_row(row):
            continue
        todo_id = table.value(row, "id")
        if not todo_id:
            continue
        rows.append(
            Todo(
                id=todo_id,
                goal=table.value(row, "goal") or "",
                subsystem=table.value(row, "subsystem") or "",
                ready=table.value(row, "ready") or "",
                done_when=table.value(row, "done when") or "",
                notes=table.value(row, "notes") or "",
            )
        )
    return tuple(rows)


def pick_todo(todos: tuple[Todo, ...], wanted: str | None = None) -> Todo | None:
    """The named row, or the first ready row. Never auto-picks on its own."""
    if wanted:
        key = wanted.strip().lower()
        return next((todo for todo in todos if todo.id.lower() == key), None)
    return next((todo for todo in todos if todo.is_ready()), None)
