"""Command implementations and helpers for the harness CLI."""

import json
import os
import re
import sys
from pathlib import Path

import questions
import record
from harness_values import (
    CleanTarget,
    ClearReport,
    DisposableTree,
    HarnessError,
    PathSet,
    config_document,
    status_report,
)


def cmd_config(paths: PathSet) -> None:
    """Emit the config document as indented JSON."""
    print(json.dumps(config_document(paths), indent=2))


def cmd_status(paths: PathSet, tree: DisposableTree) -> None:
    """Emit one line per resolved path."""
    for line in status_report(paths, tree).render_lines():
        print(line)


def cmd_clean(
    target_name: str,
    paths: PathSet,
    tree: DisposableTree,
) -> None:
    """Clear the target's roots.

    Run it inside a lane (`tools/shared/lane <subsystem> harness.py clean`) so it
    touches only that subsystem's disposable roots."""
    if target_name == "all" and not os.environ.get("SWARM_LANE"):
        raise HarnessError(
            "clean all needs a lane: run it through tools/shared/lane <subsystem>"
        )
    target = CleanTarget.parse(target_name)
    for label, root in target.roots(paths):
        removed = tree.count_entries(root)
        tree.clear(root)
        print(ClearReport(label, root, removed).render())


# --------------------------------------------------------------------------- #
# Design record: lint, question queue, render, check, batch
# --------------------------------------------------------------------------- #


def _pack_design(paths: PathSet, subsystem: str) -> Path:
    return paths.pack_root() / "design" / "subsystems" / subsystem


def _subsystem(args) -> str:
    value = (
        getattr(args, "subsystem", None) or os.environ.get("SWARM_LANE") or ""
    ).strip()
    if not value:
        raise HarnessError("no subsystem: pass --subsystem or run inside a lane")
    return value


def cmd_gen_doc(args, paths: PathSet) -> None:
    """Write the requirement document from the record, between the markers.

    The record holds the one home of each fact. The document is a view of it.
    A document with no marker is reported and left alone.
    """
    subsystem = _subsystem(args)
    record_dir = _pack_design(paths, subsystem)
    if args.specs:
        specs = Path(args.specs).expanduser().resolve()
    else:
        specs_root = paths.specs()
        specs = specs_root.require() if specs_root.is_configured() else None
    result = record.render_document(
        record_dir, specs, grow=bool(getattr(args, "grow", False))
    )
    print(f"gen-doc: {result['document']}")
    print(f"  rows: {result['rows']}   changed: {result['changed']}")
    absent = result.get("absent", [])
    if absent:
        print(f"  in the record and not in the document: {', '.join(absent)}")
    raise SystemExit(0)


def cmd_lint_record(args, paths: PathSet) -> None:
    """Lint the record for one subsystem (or an explicit record directory)."""
    if args.record:
        record_dir = Path(args.record).expanduser().resolve()
    else:
        subsystem = _subsystem(args)
        record_dir = _pack_design(paths, subsystem)
    specs = None
    if args.specs:
        specs = Path(args.specs).expanduser().resolve()
    else:
        specs_root = paths.specs()
        specs = specs_root.require() if specs_root.is_configured() else None
    report = record.lint_record_tree(record_dir, specs)
    for line in report.render_lines():
        print(line)
    print(
        f"lint-record: {len(report.errors)} error(s), {len(report.warnings)} warning(s)"
        f" -> {'pass' if report.passed() else 'fail'}"
    )
    raise SystemExit(0 if report.passed() else 2)


def _subsystem_name(args) -> str:
    """The subsystem id from --subsystem or the active lane, or '' when neither is set."""
    return (
        getattr(args, "subsystem", None) or os.environ.get("SWARM_LANE") or ""
    ).strip()


def _work_dir_for(
    paths: PathSet, role: str, subsystem: str, override: str | None
) -> Path:
    if override:
        return Path(override).expanduser().resolve()
    if not subsystem:
        raise HarnessError("no subsystem: pass --subsystem or run inside a lane")
    root = _pack_design(paths, subsystem)
    return root / questions.work_dir_for(role, root)


def cmd_check(args, paths: PathSet) -> None:
    """Lint the record the role wrote, and write the computed stop test.

    This is a *linter over the written files*, not a render step: the role fills
    the forms with its own editor and `check` reports what a defect is and how to
    fix it. It reads <SUBSYSTEM>/*.md and (for the requirements) the SPECS root.
    """
    subsystem = _subsystem_name(args)
    work = _work_dir_for(paths, args.role, subsystem, args.work)
    if not work.exists():
        raise HarnessError(f"no work path: {work} — run `init-work {args.role}` first")
    specs_root = paths.specs()
    specs = specs_root.require() if specs_root.is_configured() else None
    if work.is_file():
        report = record.lint_documents({work.name: record.Document.read(work)})
    else:
        report = record.lint_record_tree(work, specs)
    for line in report.render_lines():
        print(line)
    print(f"SUBSYSTEM: {work}")
    print(questions.render_stop_test(report))
    stop = questions.STOP_TESTS.get(args.role)
    if stop:
        print(f"STOP TEST: {stop}")
    print(
        f"check: {len(report.errors)} error(s), {len(report.warnings)} warning(s)"
        f" -> {'pass' if report.passed() else 'fail'}"
    )
    raise SystemExit(0 if report.passed() else 2)


def cmd_init_work(args, paths: PathSet) -> None:
    """Write a role's empty, self-teaching forms to a NEW subsystem's record directory.

    The subsystem record is living: a later change edits it in place and adds only
    the delta. So this refuses when the role's section files already exist — use
    `--force` only to reset a record to empty forms (destructive).
    """
    work = (
        Path(args.work).expanduser().resolve()
        if args.work
        else _pack_design(paths, _subsystem(args))
    )
    if args.role == "designer":
        target = work / "modules" / f"{getattr(args, 'module', None) or 'module'}.md"
    else:
        target = work / questions.FLAT_FILES.get(args.role, "")
    if target.is_file() and not args.force:
        raise HarnessError(
            f"the record already exists: {work} — the subsystem record is edited in "
            f"place. Read the file and add only what the change needs. "
            f"Use --force only to reset it to empty forms."
        )
    written = questions.emit_flat(args.role, work, getattr(args, "module", None))
    if not written:
        raise HarnessError(f"role {args.role} has no flat record file")
    print(f"INIT {args.role}: wrote {len(written)} flat file(s) -> {work}")


def cmd_vocab_rename(args, paths: PathSet) -> None:
    """Bulk rename a token across files, with counts and a verify pass."""
    targets: list[Path] = []
    for raw in args.files:
        path = Path(raw).expanduser()
        resolved = path if path.is_absolute() else (Path.cwd() / path)
        if resolved.is_dir():
            targets.extend(sorted(resolved.rglob("*.md")))
        elif resolved.exists():
            targets.append(resolved)
        else:
            raise HarnessError(f"no such file or directory: {raw}")
    if args.word:
        pattern = re.compile(r"\b" + re.escape(args.old) + r"\b")
    else:
        pattern = re.compile(re.escape(args.old))
    total = 0
    for path in targets:
        text = path.read_text(encoding="utf-8")
        found = len(pattern.findall(text))
        if not found:
            continue
        total += found
        if args.dry_run:
            print(f"{found:>4}  {path}")
            continue
        path.write_text(pattern.sub(args.new, text), encoding="utf-8")
        print(f"{found:>4}  {path}")
    verb = "would rename" if args.dry_run else "renamed"
    print(f"{verb} {total} occurrence(s) of {args.old!r} -> {args.new!r}")
    if args.verify and not args.dry_run:
        remaining = 0
        for path in targets:
            remaining += len(pattern.findall(path.read_text(encoding="utf-8")))
        if remaining:
            raise HarnessError(
                f"verify failed: {remaining} occurrence(s) of {args.old!r} remain"
            )
        print("verify: 0 remaining -> pass")


def _project_env_lines(paths: PathSet) -> list[str]:
    """The verbatim text of PROJECT.md's `## ENV` block, or an empty list."""
    project = paths.pack_root() / "PROJECT.md"
    if not project.exists():
        return []
    out: list[str] = []
    inside = False
    for line in project.read_text(encoding="utf-8").splitlines():
        if line.strip().lower() == "## env":
            inside = True
            continue
        if inside and line.startswith("## "):
            break
        if inside:
            out.append(line)
    while out and not out[-1].strip():
        out.pop()
    return out


def cmd_envelope(args, paths: PathSet) -> None:
    """Print a paste-ready dispatch block: every path, the ENV, and the stop-test line."""
    subsystem = (
        args.subsystem or (os.environ.get("SWARM_LANE") or "").strip() or "<subsystem>"
    )
    module = getattr(args, "module", None)
    pack = paths.pack_root()
    root = pack / "design" / "subsystems" / subsystem
    if module:
        work = root / "modules" / f"{module}.md"
        lane = f"{subsystem}.{module}"
    else:
        work = root / questions.work_dir_for(args.role, root)
        lane = subsystem
    specs_root = paths.specs()
    lines = [
        f"#PACK      {pack}",
        f"#ROLE      {args.role}",
        f"#SUBSYSTEM    {subsystem}",
        f"#LANE      {lane}",
        f"#RECORD    {root}/",
        f"#WORK      {work}{'' if module else '/'}",
        f"#TOOLS     {questions.ROLE_TOOLS.get(args.role, '')}",
        f"#SPECS     {specs_root.text() if specs_root else '(none)'}",
        f"#HARNESS   {pack / 'tools' / 'shared' / 'harness.py'}",
    ]
    if module:
        lines.append(f"#MODULE    {module}")
    template = pack / "design" / "templates" / args.role
    if template.is_dir():
        lines.append(f"#TEMPLATES {template}/")
    protocol = pack / "protocol" / (args.role + ".md")
    if protocol.exists():
        lines.append(f"#PROTOCOL  {protocol}")
    if args.role == "interrogator":
        lines.append(
            f"#METHODS   {pack / 'reference' / 'design-craft-front.md'}  "
            f"{pack / 'reference' / 'design-quality.md'}"
        )
    lines.append("")
    lines.append("#ENV")
    env = _project_env_lines(paths)
    lines.extend(env if env else ["<read PROJECT.md section ENV>"])
    stop = questions.STOP_TESTS.get(args.role)
    if stop:
        lines.append("")
        lines.append("#STOP TEST")
        lines.append(stop)
    print("\n".join(lines))


def cmd_guide(args, paths: PathSet) -> None:
    """Print the method map and the forms — the guidelines, not a driver."""
    pack = paths.pack_root()
    harness = pack / "tools" / "shared" / "harness.py"
    lane = (os.environ.get("SWARM_LANE") or "").strip()
    subsystem = args.subsystem or lane or "<subsystem>"
    role = args.role
    prefix = f"{pack}/tools/shared/lane {subsystem} python3 {harness}"
    target = questions.FLAT_FILES.get(role, "modules/<module>.md")
    lines = [
        f"GUIDE: {role} — one flat record file",
        f"PACK:    {pack}",
        f"HARNESS: {harness}",
        f"LANE:    {lane or '(none — pass --subsystem on every command)'}",
        "",
        "Every command is run as:",
        f"  {prefix} <command>",
        "",
        "HOW YOU WORK",
        f"  1. init-work {role} --subsystem {subsystem} --flat",
        f"  2. write {target} directly with your edit/write tools",
        f"  3. check {role} --subsystem {subsystem}",
        f"  4. lint-record --subsystem {subsystem}",
        f"  5. gen-doc --subsystem {subsystem}",
        f"  6. end with protocol/{role}.md, exactly",
        "",
        f"THE FILE: {target}",
        "  requirements.md    frame, goal, Rn/ACn, Cn, Xn, traceability, DECISIONs",
        "  architecture.md    module map, shared files, ## Interface sections",
        "  modules/<m>.md     contract, design, decisions",
        "  review.md          critic review",
        "  GOAL.md            orchestrator state",
        "",
        "STOP TEST",
        f"  {questions.STOP_TESTS.get(role, '')}",
        "",
        "A hole you cannot fill is a DECISION row, not an invented value.",
        "Run check and fix every finding, then end with the protocol block.",
    ]
    print("\n".join(lines))


def read_decision_rows(work: Path) -> tuple[list[dict], int, bool]:
    """The decision rows of a role's work directory, and the open count.

    One home for the parse. `cmd_decisions` (text) and the `swarm.decisions` tool
    (JSON) both read it, so the row shape never drifts.
    """
    rows: list[dict] = []
    open_count = 0
    found = False
    if work.is_file():
        candidates = [work]
    else:
        candidates = sorted(
            set(work.glob("*decisions*.md"))
            | {work / "requirements.md", work / "review.md"}
            | set((work / "modules").glob("*.md"))
        )
    for path in [item for item in candidates if item.is_file()]:
        document = record.Document.read(path)
        table = document.table_with_all("dn")
        if table is None:
            continue
        found = True
        expected = len(table.header)
        for row, line in table.rows_with_lines():
            if record._blank_row(row):
                continue
            if len(row) != expected:
                # A malformed row shifts the columns, so the answer column would be
                # misread. Surface it instead of guessing.
                rows.append(
                    {
                        "id": table.value(row, "dn"),
                        "status": "malformed",
                        "question": table.value(row, "question"),
                        "options": table.value(row, "options"),
                        "answer": None,
                        "file": path.name,
                        "line": line,
                        "cells": len(row),
                        "expected": expected,
                    }
                )
                continue
            answer = (table.value(row, "answer", "operator") or "").strip()
            is_open = record.is_placeholder(answer) or answer.lower().startswith(
                ("open", "pending", "await")
            )
            if is_open:
                open_count += 1
            rows.append(
                {
                    "id": table.value(row, "dn"),
                    "status": "open" if is_open else "answered",
                    "question": table.value(row, "question"),
                    "options": table.value(row, "options"),
                    "answer": answer or None,
                    "file": path.name,
                    "line": line,
                }
            )
    return rows, open_count, found


def cmd_decisions(args, paths: PathSet) -> None:
    """Print the decision rows of a subsystem, and the open count.

    The gate reads from one place: the role's `*-decisions.md` in WORK. The
    control block carries only the question and the answer, so this command is
    how the orchestrator fills the operator gate.
    """
    subsystem = _subsystem_name(args)
    work = _work_dir_for(paths, args.role, subsystem, args.work)
    if not work.is_dir():
        raise HarnessError(
            f"no work directory: {work} — run `init-work {args.role}` first"
        )
    rows, open_count, found = read_decision_rows(work)
    if not found:
        raise HarnessError(f"no decisions table under {work}")
    for row in rows:
        answer = row["answer"] or "-"
        print(
            f"{row['file']}:{row['line']}  {row['id']} [{row['status']}] {row['question']}  answer={answer}"
        )
    print(f"decisions: {open_count} open")


def cmd_check_envelope(args, paths: PathSet) -> None:
    """Lint a dispatch envelope: the duplicate-block rule and the cite hint.

    There is no size limit. The orchestrator cites paths and pastes only the ask.
    A long paste with no cite is a hint, never a failure.
    """
    if args.file == "-":
        text = sys.stdin.read()
    else:
        text = Path(args.file).expanduser().read_text(encoding="utf-8")
    labels = re.findall(r"^#([A-Z][A-Z ]+)$", text, re.MULTILINE)
    repeated = sorted({label for label in labels if labels.count(label) > 1})
    long_lines = [line for line in text.splitlines() if len(line) > 300]
    has_cite = bool(re.search(r"\S:\d+", text))
    print("envelope: pass (no size limit)")
    if repeated:
        print(f"warning: repeated block(s): {', '.join(repeated)}")
    if labels.count("ENV") > 1:
        print(
            "warning: #ENV appears more than once; send `same ENV as the previous dispatch`"
        )
    if long_lines and not has_cite:
        print(
            f"hint: {len(long_lines)} long line(s) and no `path:line` cite; cite the path, do not paste"
        )
    raise SystemExit(0)
