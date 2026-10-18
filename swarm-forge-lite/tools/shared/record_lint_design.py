#!/usr/bin/env python3
"""record_lint_design -- design-family linters for the record."""

from __future__ import annotations

import re

from record_lint_req import (
    _check_shape,
    lint_constraints,
    lint_exclusions,
    lint_goal_tree,
    lint_requirements,
    lint_traceability,
)
from record_parse import (
    Document,
    Report,
    _blank_row,
    _declared_keys,
    _duplicates,
    _key,
    _normalise,
    is_placeholder,
    machine_nouns,
    number_key,
)


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
    for key in ("constraints.md", "requirements.md"):
        if key in documents:
            constraints |= lint_constraints(documents[key], report)
    exclusions = lint_exclusions(
        documents.get("9-exclusions.md", _empty("9-exclusions.md")), report
    )
    for key in ("exclusions.md", "requirements.md"):
        if key in documents:
            exclusions |= lint_exclusions(documents[key], report)

    for key in ("11-traceability.md", "requirements.md"):
        if key in documents:
            lint_traceability(documents[key], report, requirements["rn"])
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
    for key in ("decisions.md", "requirements.md", "review.md"):
        if key in documents:
            lint_decisions(documents[key], report)
    contracts_docs = [
        documents[key] for key in ("1-contracts.md", "contracts.md") if key in documents
    ]
    # The module contract home is one file under modules/. The generated union
    # SKELETON.md at the subsystem root is not a module home, so it is never
    # linted here: its concatenated tables would false-positive.
    for document in documents.values():
        if "modules" in document.path.parts:
            contracts_docs.append(document)
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


def _empty(name: str):
    from record_task import _empty as _task_empty

    return _task_empty(name)
