#!/usr/bin/env python3
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PACK = HERE.parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(PACK / "tools" / "refactorer"))

import harness
import questions
import record
from swarm_support import (
    SwarmError,
    _by_code,
    _counts,
    _paths,
    _resolve_any,
    _short,
)

_WORKSPACE = PACK.parent


def cmd_status(args: dict) -> dict:
    """Resolve every root and the active lane. Compact: a map plus the missing."""
    paths = _paths()
    tree = harness.OsTree()
    report = harness.status_report(paths, tree)
    roots = {}
    missing = []
    for row in report.rows:
        roots[row.label] = _short(row.text)
        if not row.present:
            missing.append(row.label)
    out = {
        "lane": (os.environ.get("SWARM_LANE") or "").strip() or None,
        "roots": roots,
        "missing": missing,
    }
    if args.get("wiring"):
        out["wiring"] = paths.as_dict()
    return out


def _envelope_text(fields: dict, env: list[str], stop: str | None) -> str:
    lines = [f"#{k:<9} {v}" for k, v in fields.items()]
    lines.append("")
    lines.append("#ENV")
    lines.extend(env if env else ["<read PROJECT.md section ENV>"])
    if stop:
        lines += ["", "#STOP TEST", stop]
    return "\n".join(lines)


def cmd_envelope(args: dict) -> dict:
    """The paste-ready dispatch fields, the ENV, and the stop-test line."""
    role = args["role"]
    subsystem = args.get("subsystem") or "<subsystem>"
    module = args.get("module")
    paths = _paths()
    root = PACK / "design" / "subsystems" / subsystem
    if module:
        work = root / "modules" / f"{module}.md"
        lane = f"{subsystem}.{module}"
    else:
        work = root / questions.work_dir_for(role, root)
        lane = subsystem
    specs = paths.specs()
    fields = {
        "PACK": str(PACK),
        "ROLE": role,
        "SUBSYSTEM": subsystem,
        "LANE": lane,
        "SPECS": specs.text() if specs else "(none)",
        "HARNESS": str(PACK / "tools" / "shared" / "harness.py"),
    }
    # `WORK` is the design record's role directory. Only the roles the layout gives one
    # have it; the other build roles write to the source and test roots, so name their
    # reports root instead. One rule, shared with `guide`.
    fields["RECORD"] = str(root) + "/"
    if module or questions.has_work_dir(role):
        fields["WORK"] = str(work) + ("" if module else "/")
    else:
        fields["ARTIFACTS"] = str(paths.artifacts_root()) + "/"
    fields["TOOLS"] = questions.ROLE_TOOLS.get(role, "")
    template = PACK / "design" / "templates" / role
    if template.is_dir():
        fields["TEMPLATES"] = str(template) + "/"
    protocol = PACK / "protocol" / (role + ".md")
    if protocol.exists():
        fields["PROTOCOL"] = str(protocol)
    if module:
        fields["MODULE"] = str(module)
    if role == "interrogator":
        fields["METHODS"] = (
            f"{PACK / 'reference' / 'design-craft-front.md'}  "
            f"{PACK / 'reference' / 'design-quality.md'}"
        )
    env = harness._project_env_lines(paths)
    stop = questions.STOP_TESTS.get(role)
    return {
        "fields": fields,
        "env": env,
        "stop_test": stop,
        "text": _envelope_text(fields, env, stop),
    }


def _form_index(role: str) -> dict:
    spec = questions.SPECS.get(role)
    if spec is None:
        return {}
    return {section.file: section for section in spec.sections}


def _form_items(section) -> list[dict]:
    """The method of one form: its prose, then the instrument and rule of each item.

    The section FILE carries the heading and the field names alone. The method
    lives here, once, so a role reads the method from the guide and never from a
    copy of it inside every record.
    """
    items: list[dict] = []
    for part in section.parts:
        markdown = getattr(part, "markdown", None)
        if markdown is not None:
            items.append(
                {
                    "id": f"{section.file}.method",
                    "kind": "Text",
                    "instrument": "",
                    "rule": markdown.strip(),
                }
            )
            continue
        items.append(
            {
                "id": part.item_id,
                "kind": type(part).__name__,
                "instrument": getattr(part, "instrument", ""),
                "rule": getattr(part, "rule", ""),
            }
        )
    return items


def cmd_guide(args: dict) -> dict:
    """The method map: the form names, the stop test, and a fetch hint.

    Compact by default (names and titles). Pass items:true for the per-form
    instrument and rule of every item, or call `form` for one form.
    """
    role = args["role"]
    subsystem = args.get("subsystem") or "<subsystem>"
    lane = (os.environ.get("SWARM_LANE") or "").strip() or None
    root = PACK / "design" / "subsystems" / subsystem
    flat = (root / "requirements.md").is_file() or (root / "architecture.md").is_file()
    if flat and subsystem != "<subsystem>":
        if role == "designer":
            files = sorted((root / "modules").glob("*.md"))
            work = root / "modules"
        else:
            name = questions.FLAT_FILES.get(role)
            files = [root / name] if name and (root / name).is_file() else []
            work = root
        return {
            "role": role,
            "lane": lane,
            "subsystem": subsystem,
            "forms": [{"file": path.name, "title": "flat record"} for path in files],
            "stop_test": questions.STOP_TESTS.get(role),
            "next": "edit the flat file directly; run swarm.check after the edit",
            "work": str(work) + "/",
        }
    spec = questions.SPECS.get(role)
    forms: list[dict] = []
    if spec is not None:
        for section in sorted(spec.sections, key=lambda s: s.order):
            entry = {
                "file": section.file,
                "title": section.title,
                "order": section.order,
            }
            if args.get("items"):
                entry["items"] = _form_items(section)
            forms.append(entry)
    else:
        template = PACK / "design" / "templates" / role
        if template.is_dir():
            for path in sorted(template.glob("*.md")):
                if path.name != "index.md":
                    forms.append({"file": path.name, "title": "(fill this section)"})
    result = {
        "role": role,
        "lane": lane,
        "subsystem": subsystem,
        "forms": forms,
        "stop_test": questions.STOP_TESTS.get(role),
        "next": "swarm.guide({role,items:true}) for every instrument and rule",
    }
    # Same rule as `envelope`: a role with no directory in the record gets the reports
    # root, not a path the layout does not define.
    if questions.has_work_dir(role):
        result["work"] = (
            str(
                PACK
                / "design"
                / "subsystems"
                / subsystem
                / questions.work_dir_for(role)
            )
            + "/"
        )
    else:
        result["artifacts"] = str(_paths().artifacts_root()) + "/"
    return result


def _report_summary(report: record.Report) -> dict:
    errors, warnings = _counts(report)
    return {
        "passed": report.passed(),
        "errors": errors,
        "warnings": warnings,
        "byCode": _by_code([f.code for f in report.findings]),
    }


def _report_rows(report: record.Report, limit: int) -> dict:
    rows = [
        [
            f.severity,
            f.code,
            _short(f.path),
            f.line,
            f.message,
            record.HINTS.get(f.code),
        ]
        for f in report.findings
    ]
    out = {"cols": FINDING_COLS, "rows": rows[:limit]}
    if len(rows) > limit:
        out["truncated"] = True
    return out


def cmd_check(args: dict) -> dict:
    """Lint the record a role wrote, and write the computed stop test.

    Default: a verdict and the by-code tally. view:"rows" adds the findings.
    """
    role = args["role"]
    subsystem = args.get("subsystem")
    work = args.get("work")
    paths = _paths()
    if work:
        workdir = Path(work).expanduser().resolve()
    elif subsystem:
        root = PACK / "design" / "subsystems" / subsystem
        workdir = root / questions.work_dir_for(role, root)
    else:
        raise SwarmError("pass subsystem or work")
    if not workdir.exists():
        raise SwarmError(f"no work path: {workdir} — run init-work {role} first")
    specs_root = paths.specs()
    specs = specs_root.require() if specs_root.is_configured() else None
    if workdir.is_file():
        report = record.lint_documents({workdir.name: record.Document.read(workdir)})
    else:
        report = record.lint_record_tree(workdir, specs)
    out = {"role": role, "subsystem": subsystem, "work": _short(workdir)}
    out.update(_report_summary(report))
    out["ok"] = report.passed()
    out["stop_test"] = questions.render_stop_test(report)
    out["stop_test_line"] = questions.STOP_TESTS.get(role)
    if args.get("view") in ("rows", "full"):
        out.update(_report_rows(report, int(args.get("limit", 50))))
    return out


def cmd_lint_record(args: dict) -> dict:
    """Lint the accepted subsystem record (the record projection)."""
    paths = _paths()
    record_dir = args.get("record")
    subsystem = args.get("subsystem")
    if record_dir:
        target = Path(record_dir).expanduser().resolve()
    elif subsystem:
        target = PACK / "design" / "subsystems" / subsystem
    else:
        raise SwarmError("pass subsystem or record")
    if not target.is_dir():
        raise SwarmError(f"no such record: {_short(target)} — pass a real subsystem")
    specs_root = paths.specs()
    specs = (
        Path(args["specs"]).expanduser().resolve()
        if args.get("specs")
        else (specs_root.require() if specs_root.is_configured() else None)
    )
    report = record.lint_record_tree(target, specs)
    out = {"subsystem": subsystem, "record": _short(target)}
    out.update(_report_summary(report))
    out["ok"] = report.passed()
    if args.get("view") in ("rows", "full"):
        out.update(_report_rows(report, int(args.get("limit", 50))))
    return out


def cmd_gen_doc(args: dict) -> dict:
    """Sync the requirement document to the record, in place, keyed by id."""
    paths = _paths()
    subsystem = args.get("subsystem")
    record_dir = args.get("record")
    if record_dir:
        target = Path(record_dir).expanduser().resolve()
    elif subsystem:
        target = PACK / "design" / "subsystems" / subsystem
    else:
        raise SwarmError("pass subsystem or record")
    if not target.is_dir():
        raise SwarmError(f"no such record: {_short(target)} - pass a real subsystem")
    specs_root = paths.specs()
    specs = (
        Path(args["specs"]).expanduser().resolve()
        if args.get("specs")
        else (specs_root.require() if specs_root.is_configured() else None)
    )
    if specs is None:
        raise SwarmError("no SPECS root is configured")
    out = record.render_document(target, specs, grow=bool(args.get("grow")))
    out["subsystem"] = subsystem
    out["document"] = _short(Path(out["document"])) if out.get("document") else None
    return out


def cmd_decisions(args: dict) -> dict:
    """The decision rows of a subsystem and the open count.

    Default: only the OPEN rows (the ones the gate needs). all:true adds the rest.
    """
    role = args["role"]
    subsystem = args.get("subsystem")
    work = args.get("work")
    if not work and not subsystem:
        raise SwarmError("pass subsystem or work")
    if work:
        workdir = Path(work).expanduser().resolve()
    else:
        root = PACK / "design" / "subsystems" / str(subsystem)
        workdir = root / questions.work_dir_for(role, root)
    if not workdir.is_dir():
        raise SwarmError(f"no work directory: {workdir} — run init-work {role} first")
    rows, open_count, found = harness.read_decision_rows(workdir)
    if not found:
        raise SwarmError(f"no decisions table under {_short(workdir)}")
    shown = rows if args.get("all") else [r for r in rows if r["status"] == "open"]
    return {
        "role": role,
        "subsystem": subsystem,
        "open": open_count,
        "total": len(rows),
        "ok": open_count == 0,
        "rows": shown,
    }


def cmd_init_work(args: dict) -> dict:
    """Write a role's empty flat record file in a NEW subsystem."""
    role = args["role"]
    subsystem = args.get("subsystem")
    work = args.get("work")
    force = bool(args.get("force"))
    if work:
        workdir = Path(work).expanduser().resolve()
    elif subsystem:
        workdir = PACK / "design" / "subsystems" / subsystem
    else:
        raise SwarmError("pass subsystem or work")
    if role == "designer":
        target = workdir / "modules" / f"{args.get('module') or 'module'}.md"
    else:
        target = workdir / questions.FLAT_FILES.get(role, "")
    if target.is_file() and not force:
        raise SwarmError(
            f"the record already exists: {_short(workdir)} — edit it in place, "
            f"or pass force=true to reset it to empty forms"
        )
    written = questions.emit_flat(role, workdir, args.get("module"))
    if not written:
        raise SwarmError(
            f"role {role} has no flat record file; only interrogator, architect, "
            "designer, and critic call initWork"
        )
    return {
        "role": role,
        "work": _short(workdir),
        "files": [_short(path) for path in written],
    }


def cmd_clean(args: dict) -> dict:
    """Clear a disposable root of the active lane. drop:true removes an empty root."""
    target_name = args.get("target", "hot")
    paths = _paths()
    tree = harness.OsTree()
    target = harness.CleanTarget.parse(target_name)
    cleared = []
    for label, root in target.roots(paths):
        removed = tree.count_entries(root)
        tree.clear(root)
        entry = {"label": label, "path": _short(root), "removed": removed}
        if args.get("drop") and root.is_dir() and not any(root.iterdir()):
            tree.remove(root)
            entry["dropped"] = True
        cleared.append(entry)
    return {"target": target_name, "cleared": cleared}


def cmd_check_envelope(args: dict) -> dict:
    """Lint a dispatch envelope: the duplicate-block rule and the cite hint.

    There is no size limit. A long paste with no cite is a hint, not a failure.
    """
    text = args.get("text")
    if text is None and args.get("file"):
        text = Path(args["file"]).expanduser().read_text(encoding="utf-8")
    if text is None:
        raise SwarmError("pass text or file")
    labels = re.findall(r"^#([A-Z][A-Z ]+)$", text, re.MULTILINE)
    repeated = sorted({label for label in labels if labels.count(label) > 1})
    long_lines = [line for line in text.splitlines() if len(line) > 300]
    has_cite = bool(re.search(r"\S:\d+", text))
    return {
        "pass": True,
        "repeated": repeated,
        "env_twice": labels.count("ENV") > 1,
        "long_lines": len(long_lines),
        "has_cite": has_cite,
        "hint": "cite the path, do not paste"
        if (long_lines and not has_cite)
        else None,
    }


def cmd_vocab_rename(args: dict) -> dict:
    """Bulk rename a token across files, with counts and an optional verify pass."""
    old = args["old"]
    new = args["new"]
    files = args.get("files") or []
    pattern = (
        re.compile(r"\b" + re.escape(old) + r"\b")
        if args.get("word")
        else re.compile(re.escape(old))
    )
    targets: list[Path] = []
    for raw in files:
        resolved = _resolve_any(raw)
        if resolved.is_dir():
            targets.extend(sorted(resolved.rglob("*.md")))
        elif resolved.exists():
            targets.append(resolved)
        else:
            raise SwarmError(f"no such file or directory: {raw}")
    total = 0
    hits: list[dict] = []
    for path in targets:
        text = path.read_text(encoding="utf-8")
        found = len(pattern.findall(text))
        if not found:
            continue
        total += found
        hits.append({"file": _short(path), "count": found})
        if not args.get("dryRun"):
            path.write_text(pattern.sub(new, text), encoding="utf-8")
    out = {
        "old": old,
        "new": new,
        "total": total,
        "files": hits,
        "dry_run": bool(args.get("dryRun")),
    }
    if args.get("verify") and not args.get("dryRun"):
        remaining = sum(
            len(pattern.findall(p.read_text(encoding="utf-8"))) for p in targets
        )
        out["remaining"] = remaining
        out["verified"] = remaining == 0
    return out


FINDING_COLS = ["severity", "code", "file", "line", "message", "fix"]
