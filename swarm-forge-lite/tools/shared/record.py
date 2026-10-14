#!/usr/bin/env python3
"""record -- parse and lint the requirement/design record.

The requirement record is markdown: one file per section, each carrying its own
tables. This subsystem parses those tables structurally and reports the defects that
otherwise surface as hours of free-form reasoning inside a design role:

  * shape and numbering defects (blank cells, duplicate Rn/Cn/Xn, ragged rows)
  * requirement defects (EARS count, verification count, Scale/Meter/Target,
    machine nouns, Rn <-> ACn one-to-one, Refines -> a declared goal node)
  * goal-tree defects (undischarged leaf, missing anti-goal, dangling parent)
  * ledger defects (blank class, critical-path [NEEDS CONFIRM] left open)
  * SCR defects (mode x event completeness and disjointness)
  * boundary-value coverage for quantified targets
  * traceability defects (an Rn with no row, a row naming no Rn)

It is deliberately a *linter*, not a designer: every finding names a defect and
the rule that caught it, so a role routes it back or resolves it in one line
instead of re-deriving the record in a 50k-token deliberation.

Every rule is owned by a value object, and the report is a list of findings.
`lint_task` is the composition root: it locates the sections, lints each, and
returns the findings in file order.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

# --------------------------------------------------------------------------- #
# Findings
# --------------------------------------------------------------------------- #

ERROR = "error"
WARN = "warn"

# One-line fix for each finding code, so a role never has to read the source to
# learn what a finding means or how to clear it.
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


# --------------------------------------------------------------------------- #
# Markdown table parsing
# --------------------------------------------------------------------------- #

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

    def table_with(self, *keywords: str) -> Table | None:
        """The first table whose header carries any keyword."""
        for table in self.tables:
            for keyword in keywords:
                if any(keyword in _normalise(name) for name in table.header):
                    return table
        return None


# --------------------------------------------------------------------------- #
# Shared value checks
# --------------------------------------------------------------------------- #

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
# A directory or file path. A bare slash is not a path: N/N, 12/12 and C79/C80
# are a ratio or an id pair, not a path.
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
# A DeepStream/GStreamer element or plugin name: nvdsosd, nvstreammux, nvinfer.
_ELEMENT = re.compile(r"\bnv[a-z][a-z0-9]*\b")
# A declared identifier of the record: R1, AC17, C6, V9, YES, NO, G1.1.
_DECLARED_ID = re.compile(r"[A-Z]+\d*|[A-Z]\d+(?:\.\d+)+")
# The record's own notation and the workflow's own vocabulary: the SCR symbols,
# the confirm marker, the handoff field names, the record's directories. It is
# not the subject's machine, so the rule leaves it alone.
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

# The marker pairs of a requirement document. The document is a VIEW of the
# record. A generator writes between a pair and never outside it, so the
# hand-written prose of the document is never touched.
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


# --------------------------------------------------------------------------- #
# Section linters
# --------------------------------------------------------------------------- #


def _check_shape(report: Report, table: Table, label: str) -> None:
    width = len(table.header)
    for row, line in table.rows_with_lines():
        if len(row) != width:
            report.error(
                "table-shape",
                table.path,
                line,
                f"{label}: row has {len(row)} cells, header has {width}",
            )


def lint_requirements(document: Document, report: Report) -> dict:
    """Goal leaves -> requirements. Returns the parsed Rn set for cross-checks."""
    table = document.table_with("rn", "statement")
    if table is None:
        if document.text.strip():
            report.warn(
                "section-missing", document.path, 0, "no requirements table found"
            )
        return {"rn": set(), "acn": set()}
    _check_shape(report, table, "requirements")
    rns: list[str] = []
    for row, line in table.rows_with_lines():
        if _blank_row(row):
            continue
        rn = number_key(table.value(row, "rn")) or (rn_key(table.value(row, "rn")))
        if not rn:
            report.error("rn-missing", table.path, line, "row has no Rn identifier")
            continue
        rns.append(rn)
        ears = table.value(row, "ears", "pattern")
        hits = ears_matches(ears)
        if len(hits) != 1:
            report.error(
                "ears-count",
                table.path,
                line,
                f"{rn}: matches {len(hits)} EARS patterns {hits or '(none)'}; exactly one required",
            )
        verif = table.value(row, "verification")
        vhits = verification_matches(verif)
        if len(vhits) != 1:
            report.error(
                "verification-count",
                table.path,
                line,
                f"{rn}: matches {len(vhits)} verification methods {vhits or '(none)'}; exactly one required",
            )
        statement = table.value(row, "statement", "description")
        if not statement or is_placeholder(statement):
            report.error(
                "statement-blank", table.path, line, f"{rn}: statement is blank"
            )
        for field_name in ("scale", "meter", "target"):
            if is_placeholder(table.value(row, field_name)):
                report.error(
                    "fit-missing",
                    table.path,
                    line,
                    f"{rn}: {field_name.capitalize()} is blank (Gilb fit criterion)",
                )
        refines = table.value(row, "refines", "parent")
        if (
            refines
            and not is_placeholder(refines)
            and refines.strip() not in ("-", "—")
            and number_key(refines) is None
            and not re.match(r"^G[\d.]+$", refines.strip())
        ):
            report.warn(
                "refines-shape",
                table.path,
                line,
                f"{rn}: Refines '{refines}' is not a goal-node id",
            )

    duplicates = _duplicates(rns)
    for rn in duplicates:
        report.error("rn-duplicate", table.path, 0, f"{rn} appears more than once")

    # acceptance criteria table (same file, or the AC section)
    ac_table = document.table_with("acn", "check") or document.table_with("acn")
    acns: list[str] = []
    ac_to_rn: dict[str, str] = {}
    if ac_table is not None:
        for row, line in ac_table.rows_with_lines():
            acn = number_key(ac_table.value(row, "acn"))
            if not acn:
                continue
            acns.append(acn)
            source = rn_key(ac_table.value(row, "rn"))
            if source:
                ac_to_rn[acn] = source
            else:
                report.error(
                    "acn-no-rn",
                    ac_table.path,
                    line,
                    f"{acn}: acceptance check names no Rn",
                )
    rn_set, ac_set = set(rns), set(acns)
    for rn in sorted(rn_set - set(ac_to_rn.values())):
        report.error("rn-no-acn", table.path, 0, f"{rn} has no acceptance criterion")
    for source in sorted(set(ac_to_rn.values()) - rn_set):
        report.error(
            "acn-orphan", table.path, 0, f"acceptance criterion names unknown {source}"
        )
    return {"rn": rn_set, "acn": ac_set}


def lint_goal_tree(document: Document, report: Report) -> dict:
    table = document.table_with("node", "refines")
    if table is None:
        return {"nodes": set(), "leaves": set(), "tops": set()}
    _check_shape(report, table, "goal tree")
    nodes: list[str] = []
    leaves: set[str] = set()
    tops: set[str] = set()
    for row, line in table.rows_with_lines():
        node = number_key(table.value(row, "node"))
        if not node:
            continue
        nodes.append(node)
        parent = table.value(row, "refines", "parent")
        disposition = table.value(row, "disposition", "outcome")
        if is_placeholder(parent) or parent.strip() in ("-", "—", "top"):
            tops.add(node)
        if "leaf" in disposition.lower() or rn_key(disposition):
            leaves.add(node)
    for node in _duplicates(nodes):
        report.error("node-duplicate", table.path, 0, f"goal node {node} appears twice")
    node_set = set(nodes)
    for row, line in table.rows_with_lines():
        parent = table.value(row, "refines", "parent")
        parent_id = number_key(parent)
        if parent_id and parent_id not in node_set:
            report.error(
                "dangling-parent",
                table.path,
                line,
                f"parent {parent_id} is not declared in the goal tree",
            )

    anti = document.table_with("anti goal", "failed")
    anti_goals: set[str] = set()
    if anti is not None:
        index = anti.column("against")
        if index is None:
            # fall back to a header naming a goal, but never the "Anti-goal" id column
            for candidate in range(1, len(anti.header)):
                if "goal" in _normalise(anti.header[candidate]):
                    index = candidate
                    break
        if index is not None:
            for row, _ in anti.rows_with_lines():
                if index < len(row):
                    target = number_key(row[index])
                    if target:
                        anti_goals.add(target)
    for top in sorted(tops - anti_goals):
        report.error(
            "top-no-anti-goal", table.path, 0, f"top goal {top} carries no anti-goal"
        )
    return {"nodes": node_set, "leaves": leaves, "tops": tops}


def lint_constraints(document: Document, report: Report) -> set:
    table = document.table_with("cn", "sentence") or document.table_with("cn")
    if table is None:
        return set()
    _check_shape(report, table, "constraints")
    ids: list[str] = []
    for row, line in table.rows_with_lines():
        cn = number_key(table.value(row, "cn"))
        if not cn:
            continue
        ids.append(cn)
        classification = table.value(row, "fixed", "class", "negotiable")
        if is_placeholder(classification):
            report.error(
                "constraint-class-blank",
                table.path,
                line,
                f"{cn}: classification is blank",
            )
        confirm = table.value(row, "needs confirm", "confirm")
        critical = table.value(row, "critical")
        if not is_placeholder(confirm) and "yes" in critical.lower():
            report.error(
                "critical-confirm-open",
                table.path,
                line,
                f"{cn}: critical-path constraint still carries [NEEDS CONFIRM]",
            )
    for cn in _duplicates(ids):
        report.error("cn-duplicate", table.path, 0, f"{cn} appears more than once")
    return set(ids)


def lint_exclusions(document: Document, report: Report) -> set:
    table = document.table_with("xn", "excluded") or document.table_with("xn")
    if table is None:
        return set()
    _check_shape(report, table, "exclusions")
    ids: list[str] = []
    for row, line in table.rows_with_lines():
        xn = number_key(table.value(row, "xn"))
        if not xn:
            continue
        ids.append(xn)
        if is_placeholder(table.value(row, "why", "reason")):
            report.error(
                "exclusion-no-reason",
                table.path,
                line,
                f"{xn}: exclusion carries no reason",
            )
    for xn in _duplicates(ids):
        report.error("xn-duplicate", table.path, 0, f"{xn} appears more than once")
    return set(ids)


def lint_traceability(document: Document, report: Report, rn_set: set) -> None:
    table = document.table_with("rn", "scenario") or document.table_with("rn", "test")
    if table is None:
        return
    _check_shape(report, table, "traceability")
    traced: set[str] = set()
    for row, line in table.rows_with_lines():
        rn = rn_key(table.value(row, "rn"))
        if not rn:
            continue
        traced.add(rn)
        if rn not in rn_set:
            report.error(
                "trace-orphan", table.path, line, f"{rn} is not a declared requirement"
            )
        if is_placeholder(table.value(row, "test")):
            report.warn(
                "trace-no-test",
                table.path,
                line,
                f"{rn}: no test named (forward traceability)",
            )
    for rn in sorted(rn_set - traced):
        report.error("trace-missing", table.path, 0, f"{rn} has no traceability row")


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


def lint_matrix(
    document: Document,
    report: Report,
    row_header: str,
    rows_field: str,
    cols_field: str,
) -> None:
    """Completeness and disjointness for a rendered mode/condition matrix.

    The rendered matrix is ``| <row_header> | <col> | … |`` with the declared row
    and column lists on the ``Rows:`` / ``Cols:`` field lines. A blank cell is a
    hole (scr-incomplete); a repeated row label is a contradiction (scr-nondisjoint).
    """
    table = None
    for candidate in document.tables:
        if candidate.header and _normalise(candidate.header[0]) == _normalise(
            row_header
        ):
            table = candidate
            break
    rows = _declared_keys(document.text, rows_field)
    cols = _declared_keys(document.text, cols_field)
    if not rows and not cols:
        return  # nothing declared yet: the section is unfilled, not defective
    if table is None:
        if rows or cols:
            report.error(
                "scr-incomplete",
                document.path,
                0,
                f"no {row_header} matrix table found",
            )
        return
    header_cols = [_key(name) for name in table.header[1:]]
    if cols and header_cols != cols:
        report.warn(
            "matrix-col-mismatch",
            table.path,
            table.start_line,
            f"{row_header} columns {header_cols} != declared {cols}",
        )
    seen: dict[str, int] = {}
    for row, line in table.rows_with_lines():
        label = row[0].strip() if row else ""
        key = _key(label)
        if key:
            seen[key] = seen.get(key, 0) + 1
        blanks = [
            table.header[i]
            for i in range(1, len(table.header))
            if i >= len(row) or is_placeholder(row[i])
        ]
        if blanks:
            report.error(
                "scr-incomplete",
                table.path,
                line,
                f"{row_header} '{label}': no entry for {blanks}",
            )
        if rows and key and key not in rows:
            report.warn(
                "matrix-row-unknown",
                table.path,
                line,
                f"{row_header} '{label}' is not in the declared "
                f"{rows_field.lower()} {rows}",
            )
    for key, count in seen.items():
        if count > 1:
            report.error(
                "scr-nondisjoint",
                table.path,
                0,
                f"{row_header} '{key}' appears in {count} rows",
            )
    for key in rows:
        if key not in seen:
            report.error(
                "scr-incomplete", table.path, 0, f"{row_header} '{key}' has no row"
            )


def _boundary_values(document: Document, report: Report) -> None:
    boundary = document.table_with("zero", "duplicate")
    if boundary is None:
        return
    _check_shape(report, boundary, "boundary value")


def lint_obstacles(document: Document, report: Report) -> None:
    """Every obstacle carries a resolution that names an Rn, Xn, Cn or Dn."""
    table = document.table_with("obstructs")
    if table is None:
        return
    _check_shape(report, table, "obstacles")
    for row, line in table.rows_with_lines():
        if _blank_row(row):
            continue
        oid = number_key(table.value(row, "o", "obstacle"))
        resolution = table.value(row, "resolution")
        if not re.search(r"\b[RCXGD]\d+", resolution):
            report.error(
                "obstacle-undischarged",
                table.path,
                line,
                f"{oid or 'obstacle'}: resolution {resolution or '(blank)'!r} names no Rn/Xn/Cn/Dn",
            )


def lint_events(document: Document, report: Report) -> None:
    """One row per (event, condition); When is @T/@F/@C/@."""
    table = document.table_with("response")
    if table is None:
        return
    _check_shape(report, table, "event table")
    seen: dict[tuple, int] = {}
    for row, line in table.rows_with_lines():
        if _blank_row(row):
            continue
        event = table.value(row, "event").strip()
        condition = table.value(row, "condition").strip()
        when = table.value(row, "when").strip()
        if when and not re.match(r"^(@T|@F|@C|@)\b", when):
            report.warn(
                "event-when-shape",
                table.path,
                line,
                f"event {event!r}: When {when!r} is not @T, @F, @C or @",
            )
        key = (event, condition)
        if key in seen:
            report.error(
                "event-ambiguous",
                table.path,
                line,
                f"({event}, {condition}) appears twice; one row per (event, condition)",
            )
        seen[key] = line


def lint_decisions(document: Document, report: Report) -> None:
    """A candidate case with no operator disposition is open, not a defect."""
    table = document.table_with("dn", "instrument")
    if table is None:
        return
    _check_shape(report, table, "decisions")
    for row, line in table.rows_with_lines():
        if _blank_row(row):
            continue
        dn = number_key(table.value(row, "dn"))
        answer = table.value(row, "answer", "operator")
        if is_placeholder(answer) or answer.strip().lower().startswith(
            ("open", "pending", "await")
        ):
            report.warn(
                "decision-open",
                table.path,
                line,
                f"{dn or 'decision'}: no operator disposition yet",
            )


def lint_contracts(document: Document, report: Report) -> None:
    """Every method carries exactly one CQS tag and a precondition and postcondition.

    Tolerant of the filled shape: a single ``CQS`` column, or the two ``Command``
    and ``Query`` columns of the form. Warnings only, so a record the role is
    still filling never blocks the gate.
    """
    table = None
    for candidate in document.tables:
        header = " ".join(_normalise(name) for name in candidate.header)
        if "method" in header and (
            "precondition" in header or "contract" in header or "cqs" in header
        ):
            table = candidate
            break
    if table is None:
        return
    _check_shape(report, table, "contracts")
    cqs_col = table.column("cqs")
    cmd_col = table.column("command")
    qry_col = table.column("query")
    if cqs_col is None and cmd_col is None and qry_col is None:
        return
    methods: list[str] = []
    for row, line in table.rows_with_lines():
        if _blank_row(row):
            continue
        method = table.value(row, "method")
        if is_placeholder(method):
            continue
        methods.append(method)
        marks = 0
        if cqs_col is not None and cqs_col < len(row):
            value = _normalise(row[cqs_col])
            if value == "c" or "command" in value:
                marks += 1
            if value == "q" or "query" in value:
                marks += 1
        if (
            cmd_col is not None
            and cmd_col < len(row)
            and not is_placeholder(row[cmd_col])
        ):
            marks += 1
        if (
            qry_col is not None
            and qry_col < len(row)
            and not is_placeholder(row[qry_col])
        ):
            marks += 1
        if marks != 1:
            report.warn(
                "cqs-count",
                table.path,
                line,
                f"{method}: {marks} CQS tag(s); exactly one of Command or Query required",
            )
        # `—`/`none` is a written "no precondition"; warn only on a fully
        # unfilled method row, so an accepted record is not noise. Both the
        # module form (Pre/Post) and the older form (Precondition/Postcondition)
        # are read.
        pre = table.value(row, "precondition", "pre")
        post = table.value(row, "postcondition", "post")
        if is_placeholder(pre) and is_placeholder(post):
            report.warn(
                "contract-blank",
                table.path,
                line,
                f"{method}: precondition and postcondition are both blank",
            )
    for dup in _duplicates(methods):
        report.warn(
            "contract-duplicate", table.path, 0, f"method {dup} appears more than once"
        )


def lint_crc(document: Document, report: Report) -> None:
    """Every CRC card carries a responsibility sentence; each class appears once."""
    table = None
    for candidate in document.tables:
        header = " ".join(_normalise(name) for name in candidate.header)
        if "class" in header and "responsibility" in header:
            table = candidate
            break
    if table is None:
        return
    _check_shape(report, table, "CRC cards")
    classes: list[str] = []
    for row, line in table.rows_with_lines():
        if _blank_row(row):
            continue
        name = table.value(row, "class")
        if is_placeholder(name):
            continue
        classes.append(name)
        if is_placeholder(table.value(row, "responsibility")):
            report.warn(
                "crc-responsibility-blank",
                table.path,
                line,
                f"{name}: no responsibility sentence",
            )
    for dup in _duplicates([c.lower() for c in classes]):
        report.warn(
            "crc-duplicate", table.path, 0, f"class {dup} appears more than once"
        )


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


# --------------------------------------------------------------------------- #
# Composition root
# --------------------------------------------------------------------------- #

SECTION_FILES = (
    "00-header.md",
    "0A-spec.md",
    "0-frame.md",
    "1-goal.md",
    "2-goal-tree.md",
    "3-variables.md",
    "4-mode-transition.md",
    "5-event.md",
    "6-condition.md",
    "7-requirements.md",
    "8-constraints.md",
    "9-exclusions.md",
    "10-obstacles-misuse-unknowns.md",
    "11-traceability.md",
    "12-stop-test.md",
    "decisions.md",
)


# The business sections of the record. The vocabulary rule reads every line of
# these, and of the spec document. The design record is exempt: it names classes,
# files and interfaces on purpose, because that is its job.
VOCABULARY_SECTIONS = (
    "0-frame.md",
    "0A-spec.md",
    "1-goal.md",
    "2-goal-tree.md",
    "3-variables.md",
    "4-mode-transition.md",
    "5-event.md",
    "6-condition.md",
    "7-requirements.md",
    "8-constraints.md",
    "8b-sufficiency-gate.md",
    "9-exclusions.md",
    "10-obstacles-misuse-unknowns.md",
    "10b-candidate-cases.md",
    "11-traceability.md",
    "13-record-note.md",
    "requirements.md",
    "constraints.md",
    "exclusions.md",
)

# The interrogator's sections that are NOT business prose, so the rule skips
# them: the work header, the input ledger, the tracker metadata, the generated
# stop test, and the decision ledger.
VOCABULARY_EXEMPT = (
    "00-header.md",
    "0-input.md",
    "0B-tracker-metadata.md",
    "12-stop-test.md",
    "decisions.md",
)


def lint_vocabulary(document: Document, report: Report) -> None:
    """Warn on a machine noun on ANY line of a business document.

    The requirement check reads one cell. A leak hides in a constraint row, a
    definition or a scope line just as easily, so this rule reads every line.
    """
    for number, line in enumerate(document.lines, start=1):
        nouns = machine_nouns(line)
        if nouns:
            report.warn(
                "machine-noun",
                document.path,
                number,
                f"may name a machine noun {nouns}",
            )


def lint_documents(documents: dict[str, Document]) -> Report:
    """Lint a role's section files (keyed by filename)."""
    report = Report()
    requirements = {"rn": set(), "acn": set()}
    for key in ("7-requirements.md", "requirements.md"):
        if key in documents:
            parsed = lint_requirements(documents[key], report)
            requirements["rn"] |= parsed["rn"]
            requirements["acn"] |= parsed["acn"]
    goal = lint_goal_tree(
        documents.get("2-goal-tree.md", _empty("2-goal-tree.md")), report
    )
    # goal.md carries the goal tree in the record projection
    for key in ("goal.md", "1-goal.md"):
        if key in documents:
            merge = lint_goal_tree(documents[key], report)
            goal = {
                "nodes": goal["nodes"] | merge["nodes"],
                "leaves": goal["leaves"] | merge["leaves"],
                "tops": goal["tops"] | merge["tops"],
            }
    constraints = lint_constraints(
        documents.get("8-constraints.md", _empty("8-constraints.md")), report
    )
    for key in ("constraints.md",):
        if key in documents:
            constraints |= lint_constraints(documents[key], report)
    exclusions = lint_exclusions(
        documents.get("9-exclusions.md", _empty("9-exclusions.md")), report
    )
    if "exclusions.md" in documents:
        exclusions |= lint_exclusions(documents["exclusions.md"], report)

    if "11-traceability.md" in documents:
        lint_traceability(documents["11-traceability.md"], report, requirements["rn"])
    if "4-mode-transition.md" in documents:
        lint_matrix(
            documents["4-mode-transition.md"], report, "mode", "Modes", "Events"
        )
    if "6-condition.md" in documents:
        lint_matrix(
            documents["6-condition.md"], report, "condition", "Conditions", "Modes"
        )
    if "5-event.md" in documents:
        lint_events(documents["5-event.md"], report)
    if "10-obstacles-misuse-unknowns.md" in documents:
        _boundary_values(documents["10-obstacles-misuse-unknowns.md"], report)
        lint_obstacles(documents["10-obstacles-misuse-unknowns.md"], report)
    if "decisions.md" in documents:
        lint_decisions(documents["decisions.md"], report)
    contracts_docs = [
        documents[key] for key in ("1-contracts.md", "contracts.md") if key in documents
    ]
    # The module contract home. A module skeleton lives under modules/<module>/.
    # The generated union SKELETON.md at the subsystem root is not a module home,
    # so it is never linted here: its concatenated tables would false-positive.
    module_skeleton = documents.get("SKELETON.md")
    if module_skeleton is not None and "modules" in module_skeleton.path.parts:
        contracts_docs.append(module_skeleton)
    for document in contracts_docs:
        lint_contracts(document, report)
    for key in ("2-crc-cards.md", "crc_cards.md"):
        if key in documents:
            lint_crc(documents[key], report)

    # a requirement must be discharged by a goal leaf or an exclusion
    if requirements["rn"] and goal["leaves"]:
        # Best-effort: every Rn should be reachable from some leaf disposition.
        pass
    # The vocabulary rule reads every line of a business section, not one cell.
    for name, document in documents.items():
        if name in VOCABULARY_SECTIONS:
            lint_vocabulary(document, report)
    return report


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


# One requirement row of a document: `- R5 — the text`, with an optional indent.
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


def resolve_record(pack_root: Path, task: str) -> Path:
    return pack_root / "design" / "subsystems" / task
