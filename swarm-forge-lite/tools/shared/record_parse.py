#!/usr/bin/env python3
"""record_parse -- data structures, parsing, and shared helpers for the record."""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

ERROR = "error"

WARN = "warn"

HINTS = {
    "table-shape": "the row has the wrong number of cells for its header",
    "rn-missing": "give the row an Rn (R1, R2, …)",
    "ears-count": "put exactly one EARS pattern: Ubiquitous / Event-driven / State-driven / Unwanted behaviour / Optional feature",
    "verification-count": "put exactly one: test / inspection / analysis / demonstration",
    "statement-blank": "write the requirement statement",
    "machine-noun": "rephrase in business vocabulary: no code span, no path, no file name, no class or element name, no framework or library name",
    "spec-stale": "the document is a view of the record: run `swarm.genDoc` and let the row take the record's wording",
    "fit-missing": "give Scale, Meter and Target (Gilb fit criterion)",
    "rn-duplicate": "each Rn appears once",
    "rn-no-acn": "add one acceptance criterion for this Rn",
    "acn-no-rn": "name the Rn the acceptance criterion checks",
    "acn-orphan": "the acceptance criterion names an Rn that does not exist",
    "refines-shape": "Refines must name a goal-node id (G1.1)",
    "node-duplicate": "each goal node appears once",
    "dangling-parent": "the Refines parent must be a declared goal node",
    "top-no-anti-goal": "add one anti-goal for this top goal",
    "constraint-class-blank": "classify the constraint Fixed / Negotiable / Unknown",
    "critical-confirm-open": "a critical-path constraint must not carry [NEEDS CONFIRM]",
    "cn-duplicate": "each Cn appears once",
    "exclusion-no-reason": "give the exclusion a reason",
    "xn-duplicate": "each Xn appears once",
    "trace-orphan": "the row names an Rn that does not exist",
    "trace-missing": "add a traceability row for this Rn",
    "trace-no-test": "name the test that closes this Rn",
    "scr-incomplete": "every row × column cell needs exactly one entry; a blank is a hole",
    "scr-nondisjoint": "a row label appears twice; each row appears once",
    "matrix-row-unknown": "the row label is not in the declared list",
    "matrix-col-mismatch": "the columns do not match the declared list",
    "obstacle-undischarged": "resolve the obstacle by an Rn, Xn, Cn or Dn (a written resolution)",
    "event-ambiguous": "the same (event, condition) has two When values; one row per (event, condition)",
    "event-when-shape": "When must be @T, @F, @C or @",
    "decision-open": "the operator has not answered this decision yet (expected while STATE: open)",
    "cqs-count": "each method must carry exactly one CQS tag: Command or Query",
    "contract-blank": "give the method a precondition and a postcondition (invariant may be —)",
    "contract-duplicate": "each method appears once",
    "crc-responsibility-blank": "give the card one responsibility sentence",
    "crc-duplicate": "each class appears once in the CRC table",
    "no-record": "no markdown sections found",
    "section-missing": "the section has no table",
    "spec-number-duplicate": "a requirement or acceptance number repeats",
    "spec-number-gap": "a requirement or acceptance number is missing",
}


@dataclass(frozen=True)
class Finding:
    """One defect: what is wrong, where, and under which rule."""

    severity: str
    code: str
    path: Path
    line: int
    message: str

    def render(self) -> str:
        marker = "E" if self.severity == ERROR else "W"
        where = f"{self.path}:{self.line}" if self.line else str(self.path)
        hint = HINTS.get(self.code)
        tail = f"  — {hint}" if hint else ""
        return f"[{marker}] {self.code}: {where}: {self.message}{tail}"


@dataclass
class Report:
    """The ordered findings plus the counts the stop test wants to be zero."""

    findings: list[Finding] = field(default_factory=list)

    def add(self, severity, code, path, line, message) -> None:
        self.findings.append(Finding(severity, code, path, line, message))

    def error(self, code, path, line, message) -> None:
        self.add(ERROR, code, path, line, message)

    def warn(self, code, path, line, message) -> None:
        self.add(WARN, code, path, line, message)

    def extend(self, findings: Iterable[Finding]) -> None:
        self.findings.extend(findings)

    @property
    def errors(self) -> list[Finding]:
        return [f for f in self.findings if f.severity == ERROR]

    @property
    def warnings(self) -> list[Finding]:
        return [f for f in self.findings if f.severity == WARN]

    def passed(self) -> bool:
        return not self.errors

    def render_lines(self) -> list[str]:
        return [f.render() for f in self.findings]


_SEPARATOR = re.compile(r"^\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$")


@dataclass(frozen=True)
class Table:
    """One markdown table: a header, its rows, and where it starts."""

    path: Path
    start_line: int
    header: tuple[str, ...]
    rows: tuple[tuple[str, ...], ...]
    row_lines: tuple[int, ...]

    def column(self, *keywords: str) -> int | None:
        """Index of the first header cell containing any keyword (normalised)."""
        for index, name in enumerate(self.header):
            normal = _normalise(name)
            for keyword in keywords:
                if keyword in normal:
                    return index
        return None

    def value(self, row: tuple[str, ...], *keywords: str) -> str:
        index = self.column(*keywords)
        if index is None or index >= len(row):
            return ""
        return row[index].strip()

    def rows_with_lines(self) -> list[tuple[tuple[str, ...], int]]:
        return list(zip(self.rows, self.row_lines))


def _normalise(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def _split_row(line: str) -> tuple[str, ...]:
    line = line.strip()
    line = line.removeprefix("|")
    if line.endswith("|") and not line.endswith("\\|"):
        line = line[:-1]
    cells = re.split(r"(?<!\\)\|", line)
    return tuple(cell.replace("\\|", "|").strip() for cell in cells)


def parse_tables(path: Path, text: str) -> list[Table]:
    """Every markdown table in ``text``, in order."""
    lines = text.splitlines()
    tables: list[Table] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        if (
            line.lstrip().startswith("|")
            and index + 1 < len(lines)
            and _SEPARATOR.match(lines[index + 1])
        ):
            header = _split_row(line)
            rows: list[tuple[str, ...]] = []
            row_lines: list[int] = []
            cursor = index + 2
            while cursor < len(lines) and lines[cursor].lstrip().startswith("|"):
                # a row immediately followed by a separator begins a new table
                if cursor + 1 < len(lines) and _SEPARATOR.match(lines[cursor + 1]):
                    break
                rows.append(_split_row(lines[cursor]))
                row_lines.append(cursor + 1)  # 1-based
                cursor += 1
            tables.append(Table(path, index + 1, header, tuple(rows), tuple(row_lines)))
            index = cursor
        else:
            index += 1
    return tables


@dataclass(frozen=True)
class Document:
    path: Path
    text: str
    lines: tuple[str, ...]
    tables: tuple[Table, ...]

    @classmethod
    def read(cls, path: Path) -> Document:
        text = path.read_text(encoding="utf-8") if path.exists() else ""
        return cls(
            path, text, tuple(text.splitlines()), tuple(parse_tables(path, text))
        )

    @staticmethod
    def _cell_matches(name: str, keyword: str) -> bool:
        """A short id (`cn`, `rn`) matches a whole cell; a phrase matches part."""
        normal = _normalise(name)
        keyword = _normalise(keyword)
        return normal == keyword if len(keyword) <= 3 else keyword in normal

    def table_with(self, *keywords: str) -> Table | None:
        """The first table whose header carries any keyword."""
        for table in self.tables:
            for keyword in keywords:
                if any(self._cell_matches(name, keyword) for name in table.header):
                    return table
        return None

    def table_with_all(self, *keywords: str) -> Table | None:
        """The first table whose header carries every keyword.

        A merged record keeps several tables in one file. Presence-based lookup
        can then pick the wrong table (a traceability row also has an `Rn`
        header). This selector requires every keyword in the same header.
        """
        for table in self.tables:
            if all(
                any(self._cell_matches(name, keyword) for name in table.header)
                for keyword in keywords
            ):
                return table
        return None


_PLACEHOLDER = re.compile(r"^(<[^>]*>|\.{2,}|—|-|\?+|n/?a|none)?$", re.IGNORECASE)

EARS_PATTERNS = {
    "ubiquitous": ("ubiquitous",),
    "event-driven": ("event", "when"),
    "state-driven": ("state", "while"),
    "unwanted": ("unwanted", "if "),
    "optional": ("optional", "where"),
}

VERIFICATION_METHODS = ("test", "inspection", "analysis", "demonstration")

_FRAMEWORKS = (
    "gstreamer",
    "deepstream",
    "pyds",
    "pyservicemaker",
    "triton",
    "tensorrt",
    "onnx",
    "kafka",
    "opencv",
    "numpy",
    "pytest",
    "pydantic",
    "flask",
    "fastapi",
)

_FILE_EXT = re.compile(r"\w+\.(py|md|json|ya?ml|toml|cfg|ini|html|sh|feature)\b")

_PATHISH = re.compile(r"(?<![\w/])/?(?:[\w.{},-]+/)+[\w.{},-]*")


def _paths(statement: str) -> list[str]:
    """Paths in a sentence. A slash alone is a ratio or an id pair, not a path."""
    found: list[str] = []
    for match in _PATHISH.finditer(statement):
        token = match.group(0)
        if token.startswith("/") or "." in token or "_" in token:
            found.append(token.strip("`( ,"))
    return found


_IDENT = re.compile(r"\b[A-Za-z_][A-Za-z0-9_]*\b")

_ELEMENT = re.compile(r"\bnv[a-z][a-z0-9]*\b")

_DECLARED_ID = re.compile(r"[A-Z]+\d*|[A-Z]\d+(?:\.\d+)+")

WORKFLOW_TOKENS = (
    "[NEEDS CONFIRM]",
    "@",
    "@T",
    "@F",
    "@C",
    "proto.frozen",
    "proto.risks",
    "01-interrogator",
    "02-architect",
    "04-critic",
)

DOC_MARKERS = {
    "requirements": ("<!-- generated:requirements -->", "<!-- /generated -->"),
    "acceptance": ("<!-- generated:acceptance -->", "<!-- /generated -->"),
    "constraints": ("<!-- generated:constraints -->", "<!-- /generated -->"),
}


def is_placeholder(text: str) -> bool:
    return _PLACEHOLDER.match(text.strip()) is not None


def ears_matches(value: str) -> list[str]:
    normal = " " + _normalise(value) + " "
    hits = []
    for name, needles in EARS_PATTERNS.items():
        if any(needle in normal for needle in needles):
            hits.append(name)
    return hits


def verification_matches(value: str) -> list[str]:
    normal = _normalise(value)
    return [method for method in VERIFICATION_METHODS if method in normal]


def is_declared_id(span: str) -> bool:
    """True for a declared identifier of the record: R1, AC17, C6, V9, YES, G1.1."""
    return _DECLARED_ID.fullmatch(span.strip()) is not None


def machine_nouns(statement: str) -> list[str]:
    """Candidate machine nouns in a business sentence (heuristic).

    A business sentence names a value in plain words. It carries no code span, no
    path, no library name, no element name and no framework name. One exception:
    a declared identifier of the record (R1, AC17, V9, YES, G1.1).
    """
    found: list[str] = []
    spans = re.findall(r"`([^`]+)`", statement)
    lowered = statement.lower()
    for framework in _FRAMEWORKS:
        if framework in lowered:
            found.append(framework)
    for match in _FILE_EXT.finditer(statement):
        found.append(match.group(0))
    for match in _ELEMENT.finditer(statement):
        found.append(match.group(0))
    found.extend(_paths(statement))
    for token in _IDENT.findall(statement):
        if "_" in token and token.islower() and len(token) > 3 or token.endswith("()"):
            found.append(token)
    # A bare CamelCase word is often a proper name (an instrument author), so a
    # class name is flagged through its code marks, not through its shape alone.
    for span in spans:
        if not is_declared_id(span):
            found.append(f"`{span}`")
    found = [
        item for item in found if item.strip("`").rstrip("/") not in WORKFLOW_TOKENS
    ]
    # de-duplicate, keep order
    seen: list[str] = []
    for item in found:
        if item not in seen:
            seen.append(item)
    return seen


def number_key(value: str) -> str | None:
    """The leading Rn/Cn/Xn/ACn/G-node/O#/M#/D# identifier of a cell."""
    match = re.match(r"\s*\**\s*([RCXAGOMD]\d+(?:\.\d+)*|AC\d+)\b", value)
    return match.group(1) if match else None


def rn_key(value: str) -> str | None:
    match = re.search(r"\bR(\d+)\b", value)
    return f"R{match.group(1)}" if match else None


_FIELD_LINE = re.compile(r"^\s*([A-Za-z][A-Za-z ]*?):\s*(\S.*)$")


def _split_entries(value: str) -> list[str]:
    return [part.strip() for part in re.split(r"[;\n]", value) if part.strip()]


def _key(entry: str) -> str:
    match = re.match(r"^([A-Za-z]+[0-9])", entry.strip())
    return match.group(1) if match else entry.strip()


def _declared_keys(text: str, label: str) -> list[str]:
    """The keys of a rendered ``Label: a, b, c`` field line."""
    for line in text.splitlines():
        match = _FIELD_LINE.match(line)
        if match and match.group(1).strip().lower() == label.lower():
            return [_key(part) for part in _split_entries(match.group(2))]
    return []


def _duplicates(values: list[str]) -> list[str]:
    seen: set[str] = set()
    doubled: list[str] = []
    for value in values:
        if value in seen and value not in doubled:
            doubled.append(value)
        seen.add(value)
    return doubled


def _blank_row(row: tuple[str, ...]) -> bool:
    """A rendered placeholder row for an empty table is not a data row."""
    return all(is_placeholder(cell) for cell in row)
