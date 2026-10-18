"""task_board -- read the shared claim board and the deferred goal queue.

Pure parsing and overlap rules. `harness.py board` and `harness.py todo` call
these functions; the orchestrator writes the two Markdown files by hand.

The board is awareness, not a lock. A conflict means "do not start a second
writer without the operator"; it never blocks a command by itself.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import record

DEFAULT_STALE_MINUTES = 60

ACTIVE = "active"

READY_WORDS = {"yes", "y", "true", "1", "ready"}


@dataclass(frozen=True)
class Claim:
    """One row of `design/TASK_BOARD.md`."""

    id: str
    session: str
    role: str
    subsystem: str
    task: str
    files: tuple[str, ...]
    state: str
    touched: datetime | None

    def is_active(self) -> bool:
        return self.state.lower() == ACTIVE

    def is_stale(self, now: datetime, minutes: int) -> bool:
        if not self.is_active() or self.touched is None:
            return False
        return (now - self.touched).total_seconds() > minutes * 60


@dataclass(frozen=True)
class Board:
    """The parsed board header and claims."""

    updated: str | None
    stale_minutes: int
    claims: tuple[Claim, ...]


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


def _utc(text: str) -> datetime | None:
    value = (text or "").strip()
    if not value:
        return None
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    try:
        moment = datetime.fromisoformat(value)
    except ValueError:
        return None
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)
    return moment.astimezone(UTC)


def _header(text: str, label: str) -> str | None:
    match = re.search(rf"^{re.escape(label)}:\s*(.+?)\s*$", text, re.MULTILINE)
    return match.group(1) if match else None


def read_board(path: Path) -> Board:
    """Parse a board file. A missing or empty file is an empty board."""
    path = Path(path)
    if not path.is_file():
        return Board(None, DEFAULT_STALE_MINUTES, ())
    document = record.Document.read(path)
    text = document.text
    updated = _header(text, "Updated")
    stale_raw = _header(text, "Stale after")
    stale = DEFAULT_STALE_MINUTES
    if stale_raw:
        match = re.match(r"(\d+)", stale_raw)
        if match:
            stale = int(match.group(1))
    table = document.table_with("claim")
    claims: list[Claim] = []
    if table is not None:
        for row, _line in table.rows_with_lines():
            if record._blank_row(row):
                continue
            claim_id = table.value(row, "claim")
            if not claim_id:
                continue
            files = tuple(
                part.strip()
                for part in (table.value(row, "files", "allowlist") or "").split(",")
                if part.strip()
            )
            claims.append(
                Claim(
                    id=claim_id,
                    session=table.value(row, "session") or "",
                    role=table.value(row, "role") or "",
                    subsystem=table.value(row, "subsystem") or "",
                    task=table.value(row, "task") or "",
                    files=files,
                    state=(table.value(row, "state") or ACTIVE).strip(),
                    touched=_utc(table.value(row, "touched", "since") or ""),
                )
            )
    return Board(updated, stale, tuple(claims))


def _prefix(pattern: str) -> str:
    """The literal directory prefix of a glob, without a trailing slash."""
    value = pattern.strip().replace("\\", "/")
    while value.startswith("./"):
        value = value[2:]
    cuts = [value.find(char) for char in "*?[" if value.find(char) >= 0]
    end = min(cuts) if cuts else len(value)
    return value[:end].rstrip("/")


def overlaps(left: str, right: str) -> bool:
    """True when two file globs can name the same path.

    Conservative: a shared literal prefix, or a wildcard at the front, counts as
    an overlap. A false conflict asks the operator; a missed conflict corrupts.
    """
    one, two = _prefix(left), _prefix(right)
    if not one or not two or one == two:
        return True
    return one.startswith(two + "/") or two.startswith(one + "/")


def conflicts(
    board: Board,
    session: str,
    subsystem: str,
    files: tuple[str, ...],
) -> list[Claim]:
    """Active claims from another session that touch this subsystem or these files."""
    out: list[Claim] = []
    for claim in board.claims:
        if not claim.is_active() or claim.session == session:
            continue
        same_subsystem = bool(subsystem) and claim.subsystem == subsystem
        same_file = any(overlaps(one, two) for one in files for two in claim.files)
        if same_subsystem or same_file:
            out.append(claim)
    return out


def render_other(
    claims: list[Claim], now: datetime, minutes: int = DEFAULT_STALE_MINUTES
) -> str:
    """The `#OTHER SESSIONS` block the orchestrator pastes into a dispatch."""
    lines = ["#OTHER SESSIONS"]
    if not claims:
        lines.append("- none")
        return "\n".join(lines)
    for claim in claims:
        state = "stale" if claim.is_stale(now, minutes) else "active"
        files = ", ".join(claim.files) or "-"
        touched = (
            claim.touched.isoformat().replace("+00:00", "Z") if claim.touched else "-"
        )
        lines.append(
            f"- {claim.id} {claim.session} [{claim.subsystem}] {state} "
            f"{claim.task} files={files} touched={touched}"
        )
    return "\n".join(lines)


def read_todo(path: Path) -> tuple[Todo, ...]:
    """Parse the operator-owned deferred goal queue."""
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
