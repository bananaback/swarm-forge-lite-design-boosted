#!/usr/bin/env python3
"""harness -- wiring status and cleanup for the swarm-forge-lite pack.

Usage:
  harness config            print resolved wiring as JSON
  harness status            print every resolved path and the active lane
  harness clean [TARGET]    clean hot (default), state, artifacts, or all
  harness lint-record       lint a subsystem's record (or an explicit --record dir)
  harness gen-doc           sync a subsystem's requirement document to its record, keyed by id
  harness check ROLE        lint the record a role wrote, and write the computed stop test
  harness guide ROLE        print the method map and the forms
  harness init-work ROLE    write a role's empty forms to a NEW subsystem's record directory
  harness decisions ROLE    print the decision ledger of a subsystem, and the open count
  harness check-envelope    lint a dispatch envelope (duplicate blocks, the cite hint)
  harness vocab-rename      bulk rename a token across files, with a verify pass
  harness envelope ROLE     print a dispatch block with every resolved path

The CLI is a thin composition root: it loads a PathSet (over wiring) and an
OsTree (over the filesystem), then dispatches to one command. Every rule about a
value lives on that value: CleanTarget owns the target table, OptionalRoot owns
absence, and the report value objects own their rendering.
"""

import argparse
import json
import os
import re
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import questions
import record
import wiring

TARGET_NAMES: tuple = ("hot", "state", "artifacts", "all")
ABSENT_TEXT = "(none)"


class HarnessError(Exception):
    """The harness cannot resolve or act on the requested paths."""


@dataclass(frozen=True)
class OptionalRoot:
    """A resolved root that may be unconfigured; absence is a value, not None."""

    _path: Path | None = None

    def __post_init__(self) -> None:
        if self._path is not None and not isinstance(self._path, Path):
            raise HarnessError("optional root must be a Path or None")

    @classmethod
    def of(cls, path: Path | None) -> "OptionalRoot":
        return cls(path)

    def is_configured(self) -> bool:
        return self._path is not None

    def require(self) -> Path:
        if self._path is None:
            raise HarnessError("no root is configured")
        return self._path

    def text(self) -> str:
        return ABSENT_TEXT if self._path is None else str(self._path)


@dataclass(frozen=True)
class PersistentRoot:
    """One authored persistent-test root and its kind."""

    path: Path
    kind: str

    def __post_init__(self) -> None:
        if not isinstance(self.path, Path):
            raise HarnessError("persistent root path must be a Path")
        if not self.kind.strip():
            raise HarnessError("persistent root kind must not be blank")


@dataclass(frozen=True)
class CleanTarget:
    """A named set of disposable roots; owns the target-to-roots table."""

    name: str

    def __post_init__(self) -> None:
        if self.name not in TARGET_NAMES:
            raise HarnessError("unknown clean target: " + str(self.name))

    @classmethod
    def parse(cls, name: str) -> "CleanTarget":
        return cls(name)

    def roots(self, paths: "PathSet") -> tuple:
        hot = ("hot", paths.hot_tests())
        state = ("state", paths.state_root())
        artifacts = ("artifacts", paths.artifacts_root())
        table = {
            "hot": (hot,),
            "state": (state,),
            "artifacts": (artifacts,),
            "all": (hot, artifacts, state),
        }
        return table[self.name]


@dataclass(frozen=True)
class PathStatus:
    """One status line: a label, its resolved path text, and existence."""

    label: str
    text: str
    present: bool

    def __post_init__(self) -> None:
        if not self.label.strip():
            raise HarnessError("status label must not be blank")
        if not self.text.strip():
            raise HarnessError("status text must not be blank")

    def render(self) -> str:
        marker = "ok" if self.present else "-"
        return f"{self.label:<10} [{marker}] {self.text}"


@dataclass(frozen=True)
class StatusReport:
    """The ordered status lines for every resolved path."""

    rows: tuple

    def render_lines(self) -> tuple:
        return tuple(row.render() for row in self.rows)


@dataclass(frozen=True)
class ClearReport:
    """The outcome of clearing one disposable root."""

    label: str
    path: Path
    removed: int

    def __post_init__(self) -> None:
        if not self.label.strip():
            raise HarnessError("clear label must not be blank")
        if not isinstance(self.path, Path):
            raise HarnessError("clear path must be a Path")
        if self.removed < 0:
            raise HarnessError("removed count must not be negative")

    def render(self) -> str:
        plural = "y" if self.removed == 1 else "ies"
        return f"CLEANED {self.label}: {self.path} ({self.removed} entr{plural})"


class PathSet(Protocol):
    """The resolved paths the harness reads; implemented over wiring."""

    def pack_root(self) -> Path: ...
    def config_path(self) -> Path: ...
    def workspace_root(self) -> Path: ...
    def state_root(self) -> Path: ...
    def artifacts_root(self) -> Path: ...
    def hot_tests(self) -> Path: ...
    def features(self) -> OptionalRoot: ...
    def specs(self) -> OptionalRoot: ...
    def source_roots(self) -> tuple: ...
    def persistent_roots(self) -> tuple: ...
    def as_dict(self) -> dict: ...


class DisposableTree(Protocol):
    """The filesystem seam: query existence/children and clear a directory."""

    def exists(self, path: Path) -> bool: ...

    def count_entries(self, path: Path) -> int: ...

    def clear(self, path: Path) -> None: ...


class ResolvedWiring:
    """Adapt a wiring.Wiring to the PathSet port."""

    def __init__(self, resolved) -> None:
        self._resolved = resolved

    def pack_root(self) -> Path:
        return self._resolved.pack_root

    def config_path(self) -> Path:
        return self._resolved.config_path

    def workspace_root(self) -> Path:
        return self._resolved.workspace_root

    def state_root(self) -> Path:
        return self._resolved.state_root

    def artifacts_root(self) -> Path:
        return self._resolved.artifacts_root

    def hot_tests(self) -> Path:
        return self._resolved.hot_tests

    def features(self) -> OptionalRoot:
        return OptionalRoot.of(self._resolved.features)

    def specs(self) -> OptionalRoot:
        return OptionalRoot.of(self._resolved.specs)

    def source_roots(self) -> tuple:
        return tuple(self._resolved.source_roots)

    def persistent_roots(self) -> tuple:
        return tuple(
            PersistentRoot(entry["root"], entry["kind"])
            for entry in self._resolved.persistent_tests
        )

    def as_dict(self) -> dict:
        return self._resolved.as_dict()


class OsTree:
    """The real filesystem, behind the DisposableTree port."""

    def exists(self, path: Path) -> bool:
        return path.exists()

    def count_entries(self, path: Path) -> int:
        return len(list(path.iterdir())) if path.is_dir() else 0

    def clear(self, path: Path) -> None:
        path.mkdir(parents=True, exist_ok=True)
        for child in path.iterdir():
            if child.is_dir() and not child.is_symlink():
                shutil.rmtree(child)
            else:
                child.unlink()


def load_path_set(config: str | None) -> PathSet:
    """Resolve wiring and wrap it; raise HarnessError on a bad config."""
    try:
        resolved = wiring.load(config=config)
    except wiring.WiringError as error:
        raise HarnessError(str(error)) from error
    return ResolvedWiring(resolved)


def config_document(paths: PathSet) -> dict:
    """The JSON-ready document: exactly paths.as_dict()."""
    return paths.as_dict()


def status_report(paths: PathSet, tree: DisposableTree) -> StatusReport:
    """A row for every resolved path, in order."""
    rows = [
        _direct_row("PACK", paths.pack_root(), tree),
        _direct_row("CONFIG", paths.config_path(), tree),
        _lane_row(),
        _direct_row("WORKSPACE", paths.workspace_root(), tree),
        _direct_row("STATE", paths.state_root(), tree),
        _direct_row("ARTIFACTS", paths.artifacts_root(), tree),
        _direct_row("HOT", paths.hot_tests(), tree),
        _optional_row("FEATURES", paths.features(), tree),
        _optional_row("SPECS", paths.specs(), tree),
    ]
    rows.extend(_direct_row("SOURCE", root, tree) for root in paths.source_roots())
    rows.extend(_persistent_row(root, tree) for root in paths.persistent_roots())
    return StatusReport(tuple(rows))


def _direct_row(label: str, path: Path, tree: DisposableTree) -> PathStatus:
    return PathStatus(label, str(path), tree.exists(path))


def _lane_row() -> PathStatus:
    """The active lane id. Absent means no disposable isolation."""
    lane = (os.environ.get("SWARM_LANE") or "").strip()
    return PathStatus("LANE", lane or "(none)", bool(lane))


def _optional_row(label: str, root: OptionalRoot, tree: DisposableTree) -> PathStatus:
    if not root.is_configured():
        return PathStatus(label, ABSENT_TEXT, False)
    path = root.require()
    return PathStatus(label, str(path), tree.exists(path))


def _persistent_row(root: PersistentRoot, tree: DisposableTree) -> PathStatus:
    return PathStatus("PERSIST", f"{root.path} ({root.kind})", tree.exists(root.path))


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
    report = record.lint_task(record_dir, specs)
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
    return _pack_design(paths, subsystem) / questions.work_dir_for(role)


def _write_stop_test(work: Path, report: record.Report) -> None:
    if work.is_dir():
        (work / "12-stop-test.md").write_text(
            "## 12. STOP TEST — every count must be zero\n\n"
            + questions.render_stop_test(report)
            + "\n",
            encoding="utf-8",
        )


def cmd_check(args, paths: PathSet) -> None:
    """Lint the record the role wrote, and write the computed stop test.

    This is a *linter over the written files*, not a render step: the role fills
    the forms with its own editor and `check` reports what a defect is and how to
    fix it. It reads <SUBSYSTEM>/*.md and (for the requirements) the SPECS root.
    """
    subsystem = _subsystem_name(args)
    work = _work_dir_for(paths, args.role, subsystem, args.work)
    if not work.is_dir():
        raise HarnessError(
            f"no work directory: {work} — run `init-work {args.role}` first"
        )
    specs_root = paths.specs()
    specs = specs_root.require() if specs_root.is_configured() else None
    report = record.lint_task(work, specs)
    if args.role == "interrogator":
        _write_stop_test(work, report)
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
    subsystem = _subsystem_name(args)
    work = _work_dir_for(paths, args.role, subsystem, args.work)
    if work.is_dir() and any(work.glob("*.md")) and not args.force:
        raise HarnessError(
            f"the record already exists: {work} — the subsystem record is edited in "
            f"place. Read the section files and add only what the change needs. "
            f"Use --force only to reset it to empty forms."
        )
    spec = questions.SPECS.get(args.role)
    if spec is not None:
        written = questions.emit_templates(spec, work)
        print(f"INIT {args.role}: wrote {len(written)} forms -> {work}")
        return
    template = paths.pack_root() / "design" / "templates" / args.role
    if not template.is_dir():
        raise HarnessError(f"no template directory for role {args.role}: {template}")
    shutil.copytree(template, work, dirs_exist_ok=True)
    print(f"INIT {args.role}: copied the forms -> {work}")


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
    if module:
        work = pack / "design" / "subsystems" / subsystem / "modules" / str(module)
        lane = f"{subsystem}.{module}"
    else:
        work = (
            pack
            / "design"
            / "subsystems"
            / subsystem
            / questions.work_dir_for(args.role)
        )
        lane = subsystem
    specs_root = paths.specs()
    lines = [
        f"#PACK      {pack}",
        f"#ROLE      {args.role}",
        f"#SUBSYSTEM    {subsystem}",
        f"#LANE      {lane}",
        f"#WORK      {work}/",
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
    spec = questions.SPECS.get(role)
    prefix = f"{pack}/tools/shared/lane {subsystem} python3 {harness}"
    lines = [
        f"GUIDE: {role} — the forms and the method",
        f"PACK:    {pack}",
        f"HARNESS: {harness}",
        f"LANE:    {lane or '(none — pass --subsystem on every command)'}",
        "",
        "Every command is run as:",
        f"  {prefix} <command>",
        "",
        "HOW YOU WORK  (you write the files; the tool only guides and lints)",
        f"  1. init-work {role}              copy the empty forms to WORK",
        "  2. fill each section file with your normal edit/write tools. The form carries its",
        "     instrument and its rule; the method is in reference/design-craft-front.md and",
        "     reference/design-quality.md. Write the files directly — there is no cell driver.",
        f"  3. check {role}                   lint what you wrote; it writes §12 (the stop test)",
        f"  4. lint-record --subsystem {subsystem}   lint the subsystem record",
        "  5. author the requirement document docs/specs/NN-<subsystem>.md",
        "  6. end with the protocol/<role>.md block, exactly",
        "",
        "THE FORMS (in WORK, one file per section)",
    ]
    if spec:
        for section in sorted(spec.sections, key=lambda s: s.order):
            lines.append(f"  {section.file:<40} {section.title}")
    else:
        template = pack / "design" / "templates" / role
        if template.is_dir():
            for path in sorted(template.glob("*.md")):
                if path.name != "index.md":
                    lines.append(f"  {path.name:<40} (fill this section)")
    stop = questions.STOP_TESTS.get(role)
    if stop:
        lines += [
            "",
            "STOP TEST (pass line)",
            f"  {stop}",
            "  (full definition: reference/design-quality.md)",
        ]
    lines += [
        "",
        "WHAT `check` ENFORCES  (a finding is one line: [E] code: file:line: message — fix)",
    ]
    for code in sorted(record.HINTS):
        lines.append(f"  {code:<26} {record.HINTS[code]}")
    lines += [
        "",
        "WHERE IT LANDS",
        "  init-work ->  <WORK>/*.md  (the empty forms)",
        "  you write ->  <WORK>/*.md  (filled). The section files are the record.",
        "  check     ->  <WORK>/12-stop-test.md  +  finding codes on stdout",
        "  the doc   ->  docs/specs/NN-<subsystem>.md  (in the repo)",
        "",
        "THE HABIT",
        "  Write the files directly; a hole you cannot fill is a DECISION row, not an invented",
        "  value. Run `check` and fix every finding, then end with the protocol block.",
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
    for path in sorted(work.glob("*decisions*.md")):
        document = record.Document.read(path)
        table = document.table_with("dn", "instrument") or document.table_with("dn")
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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="harness")
    parser.add_argument("--config")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("config")
    sub.add_parser("status")

    clean = sub.add_parser("clean")
    clean.add_argument("target", nargs="?", choices=TARGET_NAMES, default="hot")

    lint = sub.add_parser("lint-record", help="lint a subsystem's requirement record")
    lint.add_argument("--subsystem")
    lint.add_argument("--record")
    lint.add_argument("--specs")
    gendoc = sub.add_parser(
        "gen-doc", help="write a subsystem's requirement document from its record"
    )
    gendoc.add_argument("--subsystem")
    gendoc.add_argument("--record")
    gendoc.add_argument("--specs")
    gendoc.add_argument("--grow", action="store_true")

    chk = sub.add_parser(
        "check", help="lint the record a role wrote, and write the stop test"
    )
    chk.add_argument("role")
    chk.add_argument("--subsystem")
    chk.add_argument("--work")

    guide = sub.add_parser("guide", help="print the method map and the forms")
    guide.add_argument("role")
    guide.add_argument("--subsystem")

    init = sub.add_parser(
        "init-work", help="write a role's empty forms to a NEW subsystem"
    )
    init.add_argument("role")
    init.add_argument("--subsystem")
    init.add_argument("--work")
    init.add_argument(
        "--force",
        action="store_true",
        help="reset an existing record to empty forms (destructive)",
    )

    ren2 = sub.add_parser("vocab-rename", help="bulk rename a token across files")
    ren2.add_argument("--from", "--old", dest="old", required=True)
    ren2.add_argument("--to", "--new", dest="new", required=True)
    ren2.add_argument("--in", dest="files", nargs="+", required=True)
    ren2.add_argument("--word", action="store_true", help="whole-word match")
    ren2.add_argument("--dry-run", action="store_true")
    ren2.add_argument(
        "--verify", action="store_true", help="fail if any occurrence remains"
    )

    env = sub.add_parser("envelope", help="print a dispatch block with resolved paths")
    env.add_argument("role")
    env.add_argument("--subsystem")

    dec = sub.add_parser("decisions", help="print the decision ledger of a subsystem")
    dec.add_argument("role")
    dec.add_argument("--subsystem")
    dec.add_argument("--work")

    cenv = sub.add_parser(
        "check-envelope", help="lint a dispatch envelope (no size limit)"
    )
    cenv.add_argument("file", nargs="?", default="-")

    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        paths = load_path_set(args.config)
        tree = OsTree()
        if args.command == "config":
            cmd_config(paths)
        elif args.command == "status":
            cmd_status(paths, tree)
        elif args.command == "clean":
            cmd_clean(args.target, paths, tree)
        elif args.command == "lint-record":
            cmd_lint_record(args, paths)
        elif args.command == "gen-doc":
            cmd_gen_doc(args, paths)
        elif args.command == "check":
            cmd_check(args, paths)
        elif args.command == "guide":
            cmd_guide(args, paths)
        elif args.command == "init-work":
            cmd_init_work(args, paths)
        elif args.command == "vocab-rename":
            cmd_vocab_rename(args, paths)
        elif args.command == "envelope":
            cmd_envelope(args, paths)
        elif args.command == "decisions":
            cmd_decisions(args, paths)
        elif args.command == "check-envelope":
            cmd_check_envelope(args, paths)
    except HarnessError as error:
        print(f"harness: {error}", file=sys.stderr)
        return 2
    except KeyError as error:
        print(f"harness: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
