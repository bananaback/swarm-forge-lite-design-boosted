#!/usr/bin/env python3
"""record_lint_req -- requirement-family linters for the record."""

from __future__ import annotations

import re

from record_parse import (
    Document,
    Report,
    Table,
    _blank_row,
    _duplicates,
    _normalise,
    ears_matches,
    is_placeholder,
    number_key,
    rn_key,
    verification_matches,
)


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
    table = document.table_with_all("rn", "statement")
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
    ac_table = document.table_with_all("acn", "check") or document.table_with_all("acn")
    acns: list[str] = []
    ac_to_rn: dict[str, str] = {}
    if ac_table is not None:
        _check_shape(report, ac_table, "acceptance criteria")
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
    table = document.table_with_all("cn")
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
    table = document.table_with_all("xn")
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
    table = document.table_with_all("rn", "test") or document.table_with_all(
        "rn", "scenario"
    )
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
