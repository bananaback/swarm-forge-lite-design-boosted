from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import record


@dataclass(frozen=True)
class Column:
    key: str
    label: str
    prompt: str = ""

    def header(self) -> str:
        return self.label


@dataclass(frozen=True)
class Text:
    """Static markdown between the fillable cells."""

    markdown: str


@dataclass(frozen=True)
class Field:
    """One free-text answer: a labelled line."""

    item_id: str
    label: str
    prompt: str
    instrument: str = ""
    template: str = ""
    rule: str = ""


@dataclass(frozen=True)
class Table:
    """A repeatable table: one answer is one row (a dict of column values)."""

    item_id: str
    columns: tuple[Column, ...]
    prompt: str
    instrument: str = ""
    min_rows: int = 1
    repeatable: bool = True
    rule: str = ""


@dataclass(frozen=True)
class Matrix:
    """A table whose columns come from another answer's list (modes x events)."""

    item_id: str
    row_label: str
    columns_from: str
    prompt: str
    instrument: str = ""
    column_prompt: str = ""
    min_rows: int = 1
    rule: str = ""


@dataclass(frozen=True)
class Computed:
    """A cell the harness fills from a check (the stop-test counts)."""

    item_id: str
    label: str
    renderer: Callable[[record.Report], str]


Item = Field | Table | Matrix | Computed


@dataclass(frozen=True)
class Section:
    order: int
    file: str
    title: str
    parts: tuple[Text | Item, ...]

    def items(self) -> list[Item]:
        return [part for part in self.parts if not isinstance(part, Text)]


@dataclass(frozen=True)
class RoleSpec:
    role: str
    work_dir: str
    sections: tuple[Section, ...]

    def items(self) -> list[tuple[Section, Item]]:
        out: list[tuple[Section, Item]] = []
        for section in self.sections:
            for item in section.items():
                out.append((section, item))
        return out

    def find(self, item_id: str) -> tuple[Section, Item]:
        for section, item in self.items():
            if item.item_id == item_id:
                return section, item
        raise KeyError(item_id)


# --------------------------------------------------------------------------- #
# Answer store
# --------------------------------------------------------------------------- #


def render_stop_test(report: record.Report | None) -> str:
    if report is None:
        return "(render + check first)"
    errors = sorted({f.code for f in report.errors})
    warnings = sorted({f.code for f in report.warnings})
    open_decisions = sum(1 for f in report.warnings if f.code == "decision-open")
    parts = [
        f"{len(report.errors)} error(s)" + (f": {', '.join(errors)}" if errors else "")
    ]
    parts.append(
        f"{len(report.warnings)} warning(s)"
        + (f": {', '.join(warnings)}" if warnings else "")
    )
    if open_decisions:
        parts.append(f"{open_decisions} decision(s) open at the gate")
    return ("fail — " if report.errors else "pass — ") + "; ".join(parts)


# --------------------------------------------------------------------------- #
# Progress
# --------------------------------------------------------------------------- #


def _c(key: str, label: str, prompt: str = "") -> Column:
    return Column(key, label, prompt)
