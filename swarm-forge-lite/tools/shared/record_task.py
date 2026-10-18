#!/usr/bin/env python3
"""record_task -- task orchestration for the record."""

from __future__ import annotations

import re
from pathlib import Path

from record_lint_design import lint_documents, lint_vocabulary
from record_parse import (
    Document,
    Report,
    _blank_row,
    is_placeholder,
    number_key,
)


def _empty(name: str) -> Document:
    return Document(Path(name), "", (), ())


def lint_task(record_dir: Path, specs_dir: Path | None = None) -> Report:
    """Lint the record under ``record_dir`` (and the spec doc when present)."""
    report = Report()
    documents: dict[str, Document] = {}
    if record_dir.is_dir():
        for path in sorted(record_dir.iterdir()):
            if path.suffix == ".md":
                documents[path.name] = Document.read(path)
    if not documents:
        report.warn(
            "no-record", record_dir, 0, f"no markdown sections under {record_dir}"
        )
    else:
        report.extend(lint_documents(documents).findings)
    if specs_dir is not None and specs_dir.is_dir():
        report.extend(_lint_specs(specs_dir, record_dir).findings)
    return report


REQ_LINE = re.compile(r"^\s*[-*]\s*\**\s*R(\d+)\b\s*[—:-]", re.MULTILINE)

AC_LINE = re.compile(r"^\s*[-*]\s*\**\s*AC(\d+)\b\s*[—:-]", re.MULTILINE)


def lint_record_tree(record_dir: Path, specs_dir: Path | None = None) -> Report:
    """Lint a whole subsystem: flat files at the root and nested legacy files.

    A flat record keeps its facts in requirements.md, architecture.md, review.md
    and modules/*.md. A legacy record keeps them in role directories. Both are
    read here, so a new record never needs the old ceremony and an old record
    keeps working.
    """
    report = lint_task(record_dir, specs_dir)
    if not record_dir.is_dir():
        return report
    modules = record_dir / "modules"
    if modules.is_dir():
        for path in sorted(modules.rglob("*.md")):
            report.extend(lint_documents({path.name: Document.read(path)}).findings)
    return report


def _subsystem_of(record_dir: Path) -> str:
    """The subsystem behind a record or role directory."""
    parts = record_dir.resolve().parts
    if "subsystems" in parts:
        index = parts.index("subsystems")
        if index + 1 < len(parts):
            return parts[index + 1]
    return record_dir.name


def stale_view_rows(path: Path, record_dir: Path) -> list[tuple[int, str, str]]:
    """Document rows that disagree with the record: (line, id, the record's text).

    The document is a VIEW of the record. A row that disagrees with the record is
    stale, and `genDoc` fixes it. This keeps the view honest without a hand check.
    """
    rows: dict[str, str] = {}
    for directory in (record_dir / "01-interrogator", record_dir):
        for name, key, cols in (
            ("7-requirements.md", "rn", ("statement", "sentence")),
            ("requirements.md", "rn", ("statement", "sentence")),
            ("7-requirements.md", "acn", ("check",)),
            ("requirements.md", "acn", ("check",)),
            ("8-constraints.md", "cn", ("sentence", "statement")),
            ("constraints.md", "cn", ("sentence", "statement")),
        ):
            candidate = directory / name
            if not candidate.is_file():
                continue
            for ident, words in _rows_from(Document.read(candidate), key, cols):
                rows.setdefault(ident, words)
    stale: list[tuple[int, str, str]] = []
    if not rows:
        return stale
    for number, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        match = _ROW.match(line)
        if match is None:
            continue
        ident = match.group("id")
        if ident in rows and match.group("rest").strip() != rows[ident].strip():
            stale.append((number, ident, rows[ident]))
    return stale


def _lint_specs(specs_dir: Path, record_dir: Path) -> Report:
    """Each spec document numbers its own Rn/ACn consistently, and reads clean.

    The spec docs carry their own numbering (the record's Rn are folded into the
    doc's clauses), so the numbering part checks *internal* consistency only: no
    duplicate requirement or acceptance-criteria number, no gap in the sequence,
    and an acceptance criterion for every requirement the document states.

    The spec document of THIS subsystem also gets the vocabulary rule: the
    document is read with the record, and a leak in it is a defect.
    """
    report = Report()
    subsystem = _subsystem_of(record_dir)
    for path in sorted(specs_dir.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        if subsystem and path.stem.endswith(subsystem):
            lint_vocabulary(Document.read(path), report)
            for number, ident, words in stale_view_rows(path, record_dir):
                report.warn(
                    "spec-stale",
                    path,
                    number,
                    f"{ident}: the document disagrees with the record, which reads {words!r}",
                )
        rns = [int(n) for n in REQ_LINE.findall(text)]
        acns = [int(n) for n in AC_LINE.findall(text)]
        for label, numbers in (("requirement", rns), ("acceptance criterion", acns)):
            if not numbers:
                continue
            doubled = sorted({n for n in numbers if numbers.count(n) > 1})
            if doubled:
                report.warn(
                    "spec-number-duplicate",
                    path,
                    0,
                    f"{label} number(s) repeated: {doubled}",
                )
            gaps = sorted(set(range(1, max(numbers) + 1)) - set(numbers))
            if gaps:
                report.warn(
                    "spec-number-gap",
                    path,
                    0,
                    f"{label} number(s) missing from the sequence: {gaps}",
                )
    return report


def _rows_from(
    document: Document, key: str, text_cols: tuple[str, ...]
) -> list[tuple[str, str]]:
    """The (id, text) pairs of one record table, in file order. The record's own ids."""
    table = document.table_with(key)
    if table is None:
        return []
    rows: list[tuple[str, str]] = []
    for row, _line in table.rows_with_lines():
        if _blank_row(row):
            continue
        ident = number_key(table.value(row, key))
        text = table.value(row, *text_cols)
        if ident and text and not is_placeholder(text):
            rows.append((ident, " ".join(text.split())))
    return rows


_ROW = re.compile(r"^(?P<indent>\s*)- (?P<id>(?:R|AC|C|X)\d+)\b(?: — )?(?P<rest>.*)$")


def render_document(record_dir: Path, specs_dir: Path, grow: bool = False) -> dict:
    """Sync the requirement document to the record, IN PLACE, keyed by id.

    The record holds the one home of each fact. The document is a VIEW of it. This
    rewrites each row the document already carries, using the RECORD'S OWN id and
    the record's wording, so no second numbering space can exist. Every other line
    of the document - the headings, the subheadings, the prose - stays exactly
    where it is.

    An id in the record with no row in the document is REPORTED, never written. The
    one exception is `grow=True`: it appends those rows at the end, one section for
    each id family. That is the only way a document grows, and it takes a flag.
    """
    subsystem = _subsystem_of(record_dir)
    path = None
    for candidate in sorted(specs_dir.glob("*.md")):
        if candidate.stem.endswith(subsystem):
            path = candidate
    if path is None:
        return {
            "document": None,
            "rows": 0,
            "changed": False,
            "absent": [],
            "stale": [],
            "reason": "no document for this subsystem",
        }

    # The sections live in the role directory; the record projection lives at the
    # top level. Try both, in that order.
    section_dirs = [record_dir / "01-interrogator", record_dir]
    rows: dict[str, str] = {}
    for name, key, cols in (
        ("7-requirements.md", "rn", ("statement", "sentence")),
        ("requirements.md", "rn", ("statement", "sentence")),
        ("7-requirements.md", "acn", ("check",)),
        ("requirements.md", "acn", ("check",)),
        ("8-constraints.md", "cn", ("sentence", "statement")),
        ("constraints.md", "cn", ("sentence", "statement")),
    ):
        for directory in section_dirs:
            candidate = directory / name
            if not candidate.is_file():
                continue
            for ident, words in _rows_from(Document.read(candidate), key, cols):
                rows.setdefault(ident, words)

    lines = path.read_text(encoding="utf-8").splitlines()
    out: list[str] = []
    written: list[str] = []
    index = 0
    while index < len(lines):
        match = _ROW.match(lines[index])
        ident = match.group("id") if match else None
        if ident and ident in rows:
            out.append(f"{match.group('indent')}- {ident} — {rows[ident]}")
            written.append(ident)
            index += 1
            # A row's text may wrap onto indented continuation lines. They go too.
            while (
                index < len(lines)
                and lines[index].strip()
                and lines[index].startswith(("  ", "\t"))
                and not _ROW.match(lines[index])
            ):
                index += 1
            continue
        out.append(lines[index])
        index += 1

    absent = sorted(set(rows) - set(written))
    text = "\n".join(out) + "\n"
    if grow and absent:
        # Append the rows the document lacks, one section for each id family. This
        # is the ONLY way a document grows, and it takes an explicit flag.
        family_heads = {
            "R": "## Requirements — generated",
            "AC": "## Acceptance Criteria — generated",
            "C": "## Constraints — generated",
            "X": "## Exclusions — generated",
        }

        def rank(ident: str) -> tuple[int, int]:
            letters = re.match(r"[A-Z]+", ident).group(0)
            order = ("R", "AC", "C", "X")
            return (
                order.index(letters) if letters in order else len(order),
                int(re.search(r"\d+", ident).group(0)),
            )

        grown = text.rstrip("\n").splitlines()
        family = None
        for ident in sorted(absent, key=rank):
            letters = re.match(r"[A-Z]+", ident).group(0)
            if letters != family:
                family = letters
                grown += [
                    "",
                    family_heads.get(letters, f"## {letters} — generated"),
                    "",
                ]
            grown.append(f"- {ident} — {rows[ident]}")
        text = "\n".join(grown) + "\n"

    changed = text != path.read_text(encoding="utf-8")
    if changed:
        path.write_text(text, encoding="utf-8")
    return {
        "subsystem": subsystem,
        "document": str(path),
        "rows": len(written),
        "changed": changed,
        "absent": absent,
        "stale": [],
    }
