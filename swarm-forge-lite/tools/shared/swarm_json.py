#!/usr/bin/env python3
"""swarm_json -- the machine-readable backend for the `swarm.*` Code Mode tools.

Every subcommand prints ONE JSON object on stdout. The `swarm-tools` OpenCode
plugin spawns this script and hands the parsed object to the agent, so a role
never reads prose and never pays for text it will not use.

Design rule: the DEFAULT output is small. A summary carries counts, not rows.
The caller asks for rows or for a paging handle. This keeps even a lazy
verbatim return cheap.

This subsystem is a thin composition root. It imports the same tested Python that
the shell tools use (`harness`, `record`, `questions`, `wiring`), so no rule
moves. It only reshapes a result into JSON.

Usage:
  python3 swarm_json.py <command> '<json-args>'
  python3 swarm_json.py docs            # the tool catalog and one example for each

The args JSON may carry a `subsystem` key. This script sets `SWARM_LANE` to that
value before it resolves any path, so the disposable roots of one subsystem stay
separate from every other subsystem.

On error, the script prints {"error": "<type>: <message>"} and exits 0.

Views (for the list tools: ruff, dry, crap, check, lint_record):
  summary (default)  counts and by-code tallies only
  rows               inline rows (a `cols` header plus arrays), capped by limit
  all                a paging handle; fetch more rows with `page`
"""

from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import sqlite3
import subprocess
import sys
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent  # <pack>/tools/shared
PACK = HERE.parent.parent  # <pack>
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(PACK / "tools" / "refactorer"))

import harness
import questions
import record

_WORKSPACE = PACK.parent

FINDING_COLS = ["severity", "code", "file", "line", "message", "fix"]
RUFF_COLS = ["code", "file", "line", "col", "message", "fix_applicability"]


class SwarmError(Exception):
    """A tool cannot act on the request."""


# --------------------------------------------------------------------------- #
# small helpers
# --------------------------------------------------------------------------- #


def _paths() -> harness.PathSet:
    """Resolve the wiring once, honouring the lane set in `main`."""
    return harness.load_path_set(None)


def _short(value) -> str:
    """A path relative to the workspace root when possible, to save bytes."""
    text = str(value)
    try:
        return str(Path(text).resolve().relative_to(_WORKSPACE))
    except (ValueError, OSError):
        return text


def _resolve_any(raw, paths: harness.PathSet | None = None) -> Path:
    """Resolve a relative path against the roots a caller is likely to mean."""
    path = Path(raw).expanduser()
    if path.is_absolute():
        return path
    bases: list[Path] = []
    if paths is not None:
        bases.append(Path(paths.workspace_root()))
    bases += [_WORKSPACE, PACK]
    for base in bases:
        candidate = base / raw
        if candidate.exists():
            return candidate
    return path


def _out_path(raw) -> Path:
    """Resolve an output path. The parent may not exist yet, so do not test it.

    A bare name is generated output: it belongs under the artifacts root, never at the
    workspace root or in a source tree.
    """
    path = Path(raw).expanduser()
    if path.is_absolute():
        return path
    if path.parent == Path("."):
        return _paths().artifacts_root() / path
    for base in [_WORKSPACE, PACK]:
        if (base / raw).parent.exists():
            return base / raw
    return _WORKSPACE / raw


def _run(argv, cwd=None, env=None):
    """Run a command and return (exit_code, stdout, stderr)."""
    merged = dict(os.environ)
    if env:
        merged.update(env)
    proc = subprocess.run(
        argv,
        cwd=str(cwd) if cwd else None,
        env=merged,
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.returncode, proc.stdout, proc.stderr


def _tool_env(paths: harness.PathSet) -> dict:
    """The environment a lane gives a test process, so a tool count equals a lane count.

    A role runs `<pack>/tools/shared/lane <subsystem> pytest ...` and gets
    `SWARM_TEST_DATA` plus the scoped caches. The `swarm` tools must give the
    same environment. Otherwise the tool and the role report different numbers
    for the same suite, and the role spends its time to reconcile them.
    """
    roots = [str(root.path.parent) for root in paths.persistent_roots()]
    for source in paths.source_roots():
        roots.append(str(Path(source).parent))
    existing = os.environ.get("PYTHONPATH", "")
    env = {
        "PYTHONPATH": os.pathsep.join([*roots, existing])
        if existing
        else os.pathsep.join(roots)
    }

    artifacts = paths.artifacts_root()
    scoped = {
        "SWARM_TEST_DATA": artifacts / "testdata",
        "PYTHONPYCACHEPREFIX": artifacts / "pycache",
        "TMPDIR": artifacts / "tmp",
        "HYPOTHESIS_STORAGE_DIRECTORY": artifacts / "hypothesis",
    }
    cache = artifacts / "pytest-cache"
    for path in [*scoped.values(), cache]:
        path.mkdir(parents=True, exist_ok=True)
    env.update({key: str(value) for key, value in scoped.items()})
    addopts = os.environ.get("PYTEST_ADDOPTS", "")
    env["PYTEST_ADDOPTS"] = f"-o cache_dir={cache} {addopts}".strip()
    lane = (os.environ.get("SWARM_LANE") or "").strip()
    if lane:
        env["SWARM_LANE"] = lane
    return env


def _counts(report: record.Report) -> tuple[int, int]:
    errors = sum(1 for f in report.findings if f.severity == record.ERROR)
    warnings = sum(1 for f in report.findings if f.severity == record.WARN)
    return errors, warnings


def _by_code(codes: list) -> dict:
    out: dict = {}
    for code in codes:
        key = code or "?"
        out[key] = out.get(key, 0) + 1
    return out


def _handle_dir(paths: harness.PathSet) -> Path:
    return paths.artifacts_root() / "handles"


def _save_handle(rows: list, paths: harness.PathSet, name: str) -> str:
    """Persist a full row set and return a short handle for `page`."""
    root = _handle_dir(paths)
    root.mkdir(parents=True, exist_ok=True)
    handle = uuid.uuid4().hex[:12]
    (root / f"{handle}.json").write_text(
        json.dumps({"name": name, "total": len(rows), "rows": rows}), encoding="utf-8"
    )
    return handle


def _load_handle(handle: str, paths: harness.PathSet) -> dict:
    path = _handle_dir(paths) / f"{handle}.json"
    if not path.exists():
        raise SwarmError(f"no such handle: {handle}")
    return json.loads(path.read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- #
# harness commands
# --------------------------------------------------------------------------- #


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
    if module:
        work = PACK / "design" / "subsystems" / subsystem / "modules" / str(module)
        lane = f"{subsystem}.{module}"
    else:
        work = PACK / "design" / "subsystems" / subsystem / questions.work_dir_for(role)
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
    if module or questions.has_work_dir(role):
        fields["WORK"] = str(work) + "/"
    else:
        fields["ARTIFACTS"] = str(paths.artifacts_root()) + "/"
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
        "next": "swarm.form({role, file}) for one form's items; swarm.fix({code}) for a finding fix",
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


def cmd_forms(args: dict) -> dict:
    """Just the section file names and titles of a role. The smallest method map."""
    role = args["role"]
    spec = questions.SPECS.get(role)
    if spec is not None:
        forms = [
            {"file": s.file, "title": s.title}
            for s in sorted(spec.sections, key=lambda s: s.order)
        ]
    else:
        forms = []
        template = PACK / "design" / "templates" / role
        if template.is_dir():
            forms = [
                {"file": p.name}
                for p in sorted(template.glob("*.md"))
                if p.name != "index.md"
            ]
    return {"role": role, "forms": forms, "stop_test": questions.STOP_TESTS.get(role)}


def cmd_form(args: dict) -> dict:
    """One form, with the instrument and rule of each item.

    The interrogator's forms are built from `questions`. Every other role's form is
    the template file under `design/templates/<role>/`, so the same call works for
    every role that names it.
    """
    role = args["role"]
    want = args.get("file") or args.get("form")
    index = _form_index(role)
    if index:
        section = index.get(want) if want else None
        if section is None:
            raise SwarmError(
                f"no form {want!r} for role {role}; known: {sorted(index)}"
            )
        return {
            "role": role,
            "file": section.file,
            "title": section.title,
            "items": _form_items(section),
        }
    template = PACK / "design" / "templates" / role
    if not template.is_dir():
        raise SwarmError(f"no form directory for role {role}")
    known = sorted(p.name for p in template.glob("*.md") if p.name != "index.md")
    if want is None:
        raise SwarmError(f"pass file=; {role} forms: {known}")
    path = template / want
    if not path.is_file():
        raise SwarmError(f"no form {want!r} for role {role}; known: {known}")
    return {
        "role": role,
        "file": want,
        "path": _short(path),
        "text": path.read_text(encoding="utf-8"),
    }


def cmd_fix(args: dict) -> dict:
    """The one-line fix for a finding code (or every code when none is given)."""
    if args.get("codes"):
        return {
            "fixes": [{"code": c, "fix": record.HINTS.get(c)} for c in args["codes"]]
        }
    if args.get("code"):
        return {"code": args["code"], "fix": record.HINTS.get(args["code"])}
    return {
        "fixes": [{"code": c, "fix": record.HINTS[c]} for c in sorted(record.HINTS)]
    }


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
    workdir = (
        Path(work).expanduser().resolve()
        if work
        else PACK / "design" / "subsystems" / subsystem / questions.work_dir_for(role)
    )
    if not workdir.is_dir():
        raise SwarmError(f"no work directory: {workdir} — run init-work {role} first")
    specs_root = paths.specs()
    specs = specs_root.require() if specs_root.is_configured() else None
    report = record.lint_task(workdir, specs)
    if role == "interrogator":
        harness._write_stop_test(workdir, report)
    out = {"role": role, "subsystem": subsystem, "work": _short(workdir)}
    out.update(_report_summary(report))
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
    report = record.lint_task(target, specs)
    out = {"subsystem": subsystem, "record": _short(target)}
    out.update(_report_summary(report))
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
    workdir = (
        Path(work).expanduser().resolve()
        if work
        else PACK
        / "design"
        / "subsystems"
        / str(subsystem)
        / questions.work_dir_for(role)
    )
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
        "rows": shown,
    }


def cmd_init_work(args: dict) -> dict:
    """Write a role's empty forms to a NEW subsystem's record directory."""
    role = args["role"]
    subsystem = args.get("subsystem")
    work = args.get("work")
    force = bool(args.get("force"))
    workdir = (
        Path(work).expanduser().resolve()
        if work
        else PACK / "design" / "subsystems" / subsystem / questions.work_dir_for(role)
    )
    if workdir.is_dir() and any(workdir.glob("*.md")) and not force:
        raise SwarmError(
            f"the record already exists: {_short(workdir)} — edit it in place, "
            f"or pass force=true to reset it to empty forms"
        )
    spec = questions.SPECS.get(role)
    if spec is not None:
        written = questions.emit_templates(spec, workdir)
        return {
            "role": role,
            "work": _short(workdir),
            "written": [p.name for p in written],
        }
    template = PACK / "design" / "templates" / role
    if not template.is_dir():
        raise SwarmError(f"no template directory for role {role}: {template}")
    shutil.copytree(template, workdir, dirs_exist_ok=True)
    return {"role": role, "work": _short(workdir), "copied": True}


def cmd_clean(args: dict) -> dict:
    """Clear a disposable root of the active lane."""
    target_name = args.get("target", "hot")
    paths = _paths()
    tree = harness.OsTree()
    target = harness.CleanTarget.parse(target_name)
    cleared = []
    for label, root in target.roots(paths):
        removed = tree.count_entries(root)
        tree.clear(root)
        cleared.append({"label": label, "path": _short(root), "removed": removed})
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


# --------------------------------------------------------------------------- #
# design structure: modules and frozen interfaces
# --------------------------------------------------------------------------- #


def cmd_modules(args: dict) -> dict:
    """The module map and the module/interface layout of a subsystem."""
    subsystem = args["subsystem"]
    root = PACK / "design" / "subsystems" / subsystem
    arch = root / "02-architect" / "ARCHITECTURE.md"
    ifc_dir = root / "interfaces"
    bnd_dir = root / "modules"
    interfaces = (
        sorted(p.stem for p in ifc_dir.glob("*.md")) if ifc_dir.is_dir() else []
    )
    modules = []
    if bnd_dir.is_dir():
        for child in sorted(p for p in bnd_dir.iterdir() if p.is_dir()):
            modules.append(
                {
                    "id": child.name,
                    "design": (child / "DESIGN.md").exists(),
                    "skeleton": (child / "SKELETON.md").exists(),
                }
            )
    skeleton = root / "SKELETON.md"
    return {
        "subsystem": subsystem,
        "architecture": _short(arch) if arch.exists() else None,
        "interfaces": [
            {"id": i, "path": _short(ifc_dir / (i + ".md"))} for i in interfaces
        ],
        "modules": modules,
        "split_ready": arch.exists() and len(interfaces) > 0,
        "subsystem_skeleton": _short(skeleton) if skeleton.exists() else None,
    }


def cmd_interface(args: dict) -> dict:
    """The frozen interface text of one module."""
    subsystem = args["subsystem"]
    module = args.get("module")
    if not module:
        raise SwarmError("pass module")
    path = PACK / "design" / "subsystems" / subsystem / "interfaces" / f"{module}.md"
    if not path.exists():
        raise SwarmError(f"no such interface: {_short(path)}")
    return {
        "subsystem": subsystem,
        "module": module,
        "path": _short(path),
        "text": path.read_text(encoding="utf-8"),
    }


def cmd_goal(args: dict) -> dict:
    """Read, or write, the orchestrator's scratchpad for a subsystem."""
    subsystem = args["subsystem"]
    path = PACK / "design" / "subsystems" / subsystem / "GOAL.md"
    text = args.get("text")
    if text is not None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(str(text), encoding="utf-8")
    exists = path.exists()
    return {
        "subsystem": subsystem,
        "path": _short(path),
        "exists": exists,
        "text": path.read_text(encoding="utf-8") if exists else None,
    }


# --------------------------------------------------------------------------- #
# quality commands
# --------------------------------------------------------------------------- #


def cmd_ruff(args: dict) -> dict:
    """Structured ruff findings, without the annotated source frames.

    Default: the count and the by-code tally. view:"rows" or "all" adds the rows.
    """
    paths = _paths()
    originals = args.get("paths") or []
    resolved = [str(_resolve_any(raw, paths)) for raw in originals]
    if not resolved:
        resolved = [str(p) for p in paths.source_roots()] + [
            str(root.path) for root in paths.persistent_roots()
        ]
    wrapper = PACK / "tools" / "shared" / "ruff4py"
    code, out, err = _run(
        [sys.executable, str(wrapper), "--output-format", "json", *resolved]
    )
    try:
        data = json.loads(out) if out.strip() else []
    except json.JSONDecodeError:
        return {
            "tool": "ruff",
            "error": "ruff did not return JSON",
            "stderr": err.strip()[:500],
            "exit": code,
        }
    rows = []
    for item in data:
        location = item.get("location") or {}
        rows.append(
            [
                item.get("code"),
                _short(item.get("filename", "")),
                location.get("row"),
                location.get("column"),
                item.get("message"),
                (item.get("fix") or {}).get("applicability"),
            ]
        )
    result = {
        "tool": "ruff",
        "total": len(rows),
        "byCode": _by_code([r[0] for r in rows]),
        "exit": code,
    }
    view = args.get("view", "summary")
    if view in ("rows", "full"):
        limit = int(args.get("limit", 50))
        result["cols"] = RUFF_COLS
        result["rows"] = rows[:limit]
        if len(rows) > limit:
            result["truncated"] = True
            result["handle"] = _save_handle(rows, paths, "ruff")
    elif view == "all":
        result["handle"] = _save_handle(rows, paths, "ruff")
        result["note"] = "fetch more rows with swarm.page({handle})"
    return result


def cmd_format(args: dict) -> dict:
    """Files `ruff format --check` would rewrite. Default: the count.

    Ruff discovers the repository config from each file's own directory. The
    cache stays under the artifacts root, so nothing lands in the project tree.
    """
    paths = _paths()
    originals = args.get("paths") or []
    resolved = [str(_resolve_any(raw, paths)) for raw in originals]
    if not resolved:
        resolved = [str(p) for p in paths.source_roots()] + [
            str(root.path) for root in paths.persistent_roots()
        ]
    cache = paths.artifacts_root() / "ruff-cache"
    argv = [
        sys.executable,
        "-m",
        "ruff",
        "format",
        "--check",
        "--cache-dir",
        str(cache),
        *resolved,
    ]
    code, out, err = _run(argv)
    match = re.search(r"(\d+) files? would be reformatted", out)
    count = int(match.group(1)) if match else 0
    result = {"tool": "ruff-format", "total": count, "exit": code}
    if err.strip():
        result["stderr"] = err.strip()[:300]
    return result


DRY_NAME = "dryer"
DRY_THRESHOLD = "0.82"
DRY_MIN_LINES = 4
DRY_MIN_NODES = 20


def _dry_pairs(output: str) -> list:
    """The duplicate pairs of a dryer report, one [first, second] per block."""
    pairs = []
    for block in re.split(r"\n\s*\n", output.strip()):
        pos = re.findall(r"^\s*(.+?):(\d+)-(\d+)\s*$", block, re.MULTILINE)
        if len(pos) == 2:
            pairs.append(
                [
                    f"{_short(pos[0][0])}:{pos[0][1]}-{pos[0][2]}",
                    f"{_short(pos[1][0])}:{pos[1][1]}-{pos[1][2]}",
                ]
            )
    return pairs


def _dry_env(paths: harness.PathSet) -> dict:
    """The lane environment plus the vendored dryer package on PYTHONPATH."""
    env = _tool_env(paths)
    tools = str(PACK / "tools" / "shared")
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = os.pathsep.join([tools, existing]) if existing else tools
    return env


def _dry_argv(paths: harness.PathSet, args: dict) -> list:
    """The vendored dryer command, at the pack's DRY settings.

    `--root` is the artifacts root, so the `.metrics/dry.edn` snapshot lands
    under `dump/` and never in the source tree.
    """
    return [
        sys.executable,
        "-m",
        DRY_NAME,
        "--root",
        str(paths.artifacts_root()),
        "--threshold",
        str(args.get("threshold", DRY_THRESHOLD)),
        "--min-lines",
        str(args.get("minLines", DRY_MIN_LINES)),
        "--min-nodes",
        str(args.get("minNodes", DRY_MIN_NODES)),
    ]


def cmd_dry(args: dict) -> dict:
    """Duplicate-code pairs. Default: the count. view:"rows" adds the pairs."""
    paths = _paths()
    originals = args.get("paths") or [str(p) for p in paths.source_roots()]
    resolved = [str(_resolve_any(raw, paths)) for raw in originals]
    argv = _dry_argv(paths, args) + resolved
    code, out, err = _run(argv, env=_dry_env(paths))
    pairs = _dry_pairs(out)
    result = {"tool": DRY_NAME, "total": len(pairs), "exit": code}
    view = args.get("view", "summary")
    if view in ("rows", "full"):
        limit = int(args.get("limit", 50))
        result["pairs"] = pairs[:limit]
        if len(pairs) > limit:
            result["truncated"] = True
            result["handle"] = _save_handle(pairs, paths, "dry")
    elif view == "all":
        result["handle"] = _save_handle(pairs, paths, "dry")
    if err.strip():
        result["stderr"] = err.strip()[:300]
    return result


CRAP_THRESHOLD = 10.0
CRAP_NAME = "crapper"

_CRAP_ROW = re.compile(
    r"^(?P<fn>.*?)\s+(?P<ns>\S+)\s+(?P<cc>\d+)\s+(?P<cov>\S+)\s+(?P<crap>\S+)\s*$"
)


def _crap_value(text: str) -> float | None:
    try:
        return float(text)
    except ValueError:
        return None


def _crap_rows(output: str) -> list:
    """The report rows of a crapper run, worst first."""
    rows = []
    for line in output.splitlines():
        match = _CRAP_ROW.match(line)
        if not match:
            continue
        rows.append(
            {
                "function": match.group("fn").strip(),
                "namespace": match.group("ns"),
                "cc": int(match.group("cc")),
                "coverage": match.group("cov"),
                "crap": match.group("crap"),
            }
        )
    return rows


def _crap_over(rows: list) -> list:
    """The rows whose CRAP score is above the pack's threshold."""
    return [row for row in rows if (_crap_value(row["crap"]) or 0.0) > CRAP_THRESHOLD]


def _newest_python_mtime(roots) -> float:
    """The newest mtime of a .py file under the given roots."""
    newest = 0.0
    skip = {"__pycache__", ".pytest_cache", ".hypothesis", ".git", ".ruff_cache"}
    for raw in roots:
        base = Path(raw)
        if not base.exists():
            continue
        candidates = base.rglob("*.py") if base.is_dir() else [base]
        for path in candidates:
            if any(part in skip for part in path.parts):
                continue
            try:
                newest = max(newest, path.stat().st_mtime)
            except OSError:
                continue
    return newest


def _crap_report(root: Path) -> Path:
    """Where the pack's coverage run writes the report crapper reads."""
    return root / "target" / "coverage" / "python" / "lcov.info"


def _crap_coverage_fresh(paths, root: Path, sources) -> bool:
    """True when the coverage report is newer than every source and test file."""
    report = _crap_report(root)
    if not report.exists():
        return False
    watched = list(sources) + [str(entry.path) for entry in paths.persistent_roots()]
    newest = _newest_python_mtime(watched)
    return newest > 0.0 and report.stat().st_mtime >= newest


def _crap_coverage_command(paths, root: Path) -> str:
    """The coverage.py command that writes the report crapper reads.

    crapper runs it in a shell, in the artifacts root. The ';' keeps the lcov
    report even when the tests fail, so the run reports the coverage it did get.
    """
    data = _crap_report(root).parent / ".coverage"
    tests = [str(entry.path) for entry in paths.persistent_roots()]
    run = [
        sys.executable,
        "-m",
        "coverage",
        "run",
        f"--data-file={data}",
        "-m",
        "pytest",
        "-p",
        "no:cacheprovider",
        *tests,
    ]
    lcov = [
        sys.executable,
        "-m",
        "coverage",
        "lcov",
        f"--data-file={data}",
        "-o",
        str(_crap_report(root)),
    ]
    return " ; ".join(
        " ".join(shlex.quote(part) for part in cmd) for cmd in (run, lcov)
    )


def _crap_env(paths) -> dict:
    """The lane environment plus the vendored crapper package on PYTHONPATH."""
    env = _tool_env(paths)
    tools = str(PACK / "tools" / "refactorer")
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = os.pathsep.join([tools, existing]) if existing else tools
    return env


def _crap_argv(paths, args) -> list:
    """The vendored crapper command, at the pack's CRAP 10 threshold."""
    root = paths.artifacts_root()
    sources = args.get("sourceRoot") or [str(p) for p in paths.source_roots()]
    argv = [
        sys.executable,
        "-m",
        CRAP_NAME,
        "--root",
        str(root),
        "--threshold",
        f"{CRAP_THRESHOLD:.0f}",
    ]
    for source in sources:
        argv += ["--source-root", str(source)]
    reuse = args.get("useExisting") or (
        args.get("reuseFresh") and _crap_coverage_fresh(paths, root, sources)
    )
    if reuse:
        argv.append("--use-existing-coverage")
    else:
        _crap_report(root).parent.mkdir(parents=True, exist_ok=True)
        argv += ["--coverage-command", _crap_coverage_command(paths, root)]
    argv += list(args.get("filters") or [])
    return argv


def cmd_crap(args: dict) -> dict:
    """CRAP (complexity x coverage). Default: only the rows above the threshold."""
    paths = _paths()
    code, out, err = _run(_crap_argv(paths, args), env=_crap_env(paths))
    rows = _crap_rows(out)
    result = {
        "tool": CRAP_NAME,
        "threshold": CRAP_THRESHOLD,
        "total": len(rows),
        "above": len(_crap_over(rows)),
        "rows": rows if args.get("all") else _crap_over(rows),
        "exit": code,
    }
    if err.strip():
        result["stderr"] = err.strip()[:300]
    return result


_SUMMARY = re.compile(r"(\d+)\s+(passed|failed|error|errors|skipped|xfailed|xpassed)")


def _pytest_summary(out: str) -> dict:
    summary_line = None
    for line in reversed(out.splitlines()):
        if _SUMMARY.search(line) and (
            "passed" in line or "failed" in line or "error" in line
        ):
            summary_line = line.strip().strip("=").strip()
            break
    tallies: dict[str, int] = {}
    if summary_line:
        for count, word in _SUMMARY.findall(summary_line):
            key = "errors" if word in ("error", "errors") else word
            tallies[key] = tallies.get(key, 0) + int(count)
    failures = []
    seen: set[str] = set()
    for line in out.splitlines():
        match = re.match(r"^(FAILED|ERROR)\s+(\S+)(?:\s+-\s+(.*))?$", line)
        if match and match.group(2) not in seen:
            seen.add(match.group(2))
            failures.append(
                {"test": match.group(2), "reason": (match.group(3) or "").strip()[:200]}
            )
    return {"summary": summary_line, "tallies": tallies, "failures": failures}


def cmd_pytest(args: dict) -> dict:
    """Run pytest and return counts and failing tests, not the whole log."""
    paths = _paths()
    roots = paths.persistent_roots()
    if not roots:
        raise SwarmError("no persistent test root configured")
    persist = roots[0].path
    argv = [
        sys.executable,
        "-m",
        "pytest",
        "-q",
        "-rf",
        "--tb=line",
        "-p",
        "no:cacheprovider",
    ]
    if args.get("k"):
        argv += ["-k", str(args["k"])]
    selected = args.get("paths") or []
    full = args.get("scope") == "full"
    for raw in selected:
        candidate = Path(raw)
        argv.append(str(candidate if candidate.is_absolute() else persist / raw))
    if not selected and not full and not args.get("k"):
        full = True
    code, out, _err = _run(argv, cwd=persist, env=_tool_env(paths))
    parsed = _pytest_summary(out)
    return {
        "tool": "pytest",
        "scope": "full" if full else "scoped",
        "passed": parsed["tallies"].get("passed", 0),
        "failed": parsed["tallies"].get("failed", 0),
        "errors": parsed["tallies"].get("errors", 0),
        "skipped": parsed["tallies"].get("skipped", 0),
        "failures": parsed["failures"],
        "summary": parsed["summary"],
        "exit": code,
    }


def cmd_acceptance(args: dict) -> dict:
    """Run the acceptance pipeline for one feature or all features."""
    paths = _paths()
    roots = paths.persistent_roots()
    if not roots:
        raise SwarmError("no persistent test root configured")
    tests_dir = roots[0].path
    runner = tests_dir / "acceptance" / "run_acceptance.py"
    if not runner.exists():
        raise SwarmError(f"no acceptance runner: {_short(runner)}")
    argv = [sys.executable, str(runner)]
    if args.get("feature") and args["feature"] != "*":
        argv.append(str(args["feature"]))
    code, out, _err = _run(argv, cwd=tests_dir, env=_tool_env(paths))
    stems = re.findall(r"^=== (\S+): parse ===$", out, re.MULTILINE)
    parsed = _pytest_summary(out)
    return {
        "tool": "run_acceptance",
        "features": stems,
        "passed": parsed["tallies"].get("passed", 0),
        "failed": parsed["tallies"].get("failed", 0),
        "failures": parsed["failures"],
        "summary": parsed["summary"],
        "exit": code,
    }


def cmd_gherkin_parse(args: dict) -> dict:
    """Parse a .feature file to the JSON IR and summarize it."""
    paths = _paths()
    features = paths.features()
    if features is None or not features.is_configured():
        raise SwarmError("no features root configured")
    stem = args["feature"]
    feature = Path(stem)
    if not feature.is_absolute():
        feature = features.require() / f"{stem}.feature"
    if not feature.is_file():
        raise SwarmError(f"no such feature: {_short(feature)}")
    ir = paths.artifacts_root() / f"{feature.stem}.json"
    argv = [str(PACK / "tools" / "shared" / "gherkin-parser"), str(feature), str(ir)]
    code, _out, err = _run(argv)
    result = {"feature": _short(feature), "ir": _short(ir), "exit": code}
    if code == 0 and ir.exists():
        try:
            data = json.loads(ir.read_text(encoding="utf-8"))
            scenarios = [s.get("name") for s in data.get("scenarios", [])]
            result["scenario_count"] = len(scenarios)
            if args.get("names"):
                result["scenarios"] = scenarios
        except (json.JSONDecodeError, OSError):
            pass
    if err.strip():
        result["stderr"] = err.strip()[:300]
    return result


def _resolve_artifacts_path(raw: str, paths):
    """Find a path a caller named, under the artifacts root or the workspace root.

    `swarm.gherkinParse` returns a path relative to the workspace root and
    `swarm.gherkinDry` takes one relative to the artifacts root, so both resolve here
    and the two tools chain.
    """
    p = Path(raw)
    if p.is_absolute():
        return p if p.is_file() else None
    for base in (paths.artifacts_root(), _WORKSPACE, Path.cwd()):
        candidate = base / p
        if candidate.is_file():
            return candidate
    return None


def cmd_gherkin_dry(args: dict) -> dict:
    """Run the IR dry-checker and summarize the report.

    `ir` accepts the name under the artifacts root, or any path that resolves: the
    `swarm.gherkinParse` result passes straight through.
    """
    paths = _paths()
    ir = _resolve_artifacts_path(args["ir"], paths)
    if ir is None:
        raise SwarmError(f"no such IR: {_short(paths.artifacts_root() / args['ir'])}")
    report_path = ir.with_suffix(".dry.json")
    argv = [str(PACK / "tools" / "specifier" / "ir-dry-checker")]
    if args.get("includeExact"):
        argv.append("--include-exact")
    argv += [str(ir), str(report_path)]
    code, _out, _err = _run(argv)
    result = {"ir": _short(ir), "exit": code}
    if code == 0 and report_path.exists():
        try:
            data = json.loads(report_path.read_text(encoding="utf-8"))
            findings = data.get("findings") or data.get("checks") or []
            result["counts"] = _by_code(
                [f.get("kind") or f.get("rule") for f in findings]
            )
            result["total"] = len(findings)
            if args.get("view") in ("rows", "full") or args.get("full"):
                limit = int(args.get("limit", 10))
                result["findings"] = findings[:limit]
                result["truncated"] = len(findings) > limit
        except (json.JSONDecodeError, OSError):
            pass
    return result


# --------------------------------------------------------------------------- #
# umlview commands
# --------------------------------------------------------------------------- #


def _resolve_model(raw: str, subsystem: str | None) -> Path:
    path = Path(raw)
    if path.is_absolute():
        return path
    if subsystem:
        return PACK / "design" / "subsystems" / subsystem / raw
    return path


def cmd_uml_render(args: dict) -> dict:
    """Render model.json to a standalone model.html."""
    model = _resolve_model(args["model"], args.get("subsystem"))
    argv = [
        sys.executable,
        str(PACK / "tools" / "shared" / "umlview" / "render.py"),
        str(model),
    ]
    if args.get("out"):
        argv += ["--out", str(_out_path(args["out"]))]
    if args.get("check"):
        argv.append("--check")
    code, out, err = _run(argv)
    return {
        "tool": "umlview-render",
        "model": _short(model),
        "exit": code,
        "stdout": out.strip() or None,
        "stderr": err.strip() or None,
    }


def cmd_uml_sync(args: dict) -> dict:
    """Overlay the real signatures and CRAP metrics onto the model."""
    model = _resolve_model(args["model"], args.get("subsystem"))
    paths = _paths()
    argv = [
        sys.executable,
        str(PACK / "tools" / "shared" / "umlview" / "sync_python.py"),
        str(model),
        "--source",
        str(
            _resolve_any(args["source"], paths)
            if args.get("source")
            else (paths.source_roots()[0] if paths.source_roots() else ".")
        ),
    ]
    if args.get("crap"):
        argv += ["--crap", str(_resolve_any(args["crap"], paths))]
    if args.get("out"):
        argv += ["--out", str(_out_path(args["out"]))]
    code, out, err = _run(argv)
    return {
        "tool": "umlview-sync",
        "model": _short(model),
        "exit": code,
        "stdout": out.strip() or None,
        "stderr": err.strip() or None,
    }


def cmd_uml_scan(args: dict) -> dict:
    """Scan a Python source root into a model.json.

    The output lands under the artifacts root by default. The scanned root is the
    SOURCE tree, and a generated model must never be written into it.
    """
    paths = _paths()
    root = _resolve_any(args["root"], paths)
    argv = [
        sys.executable,
        str(PACK / "tools" / "shared" / "umlview" / "scan_python.py"),
        str(root),
    ]
    for key in ("prefix", "title"):
        if args.get(key):
            argv += [f"--{key}", str(args[key])]
    out = (
        _out_path(args["out"])
        if args.get("out")
        else paths.artifacts_root() / "model.scan.json"
    )
    argv += ["--out", str(out)]
    code, out, err = _run(argv)
    return {
        "tool": "umlview-scan",
        "root": _short(root),
        "exit": code,
        "stdout": out.strip() or None,
        "stderr": err.strip() or None,
    }


def _uml_model_path(raw, subsystem) -> Path:
    """Resolve a model path: absolute, subsystem-relative, pack, then workspace."""
    path = Path(raw).expanduser()
    if path.is_absolute():
        return path
    candidates = []
    if subsystem:
        candidates.append(PACK / "design" / "subsystems" / str(subsystem) / raw)
    candidates += [PACK / raw, _WORKSPACE / raw, Path.cwd() / raw]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return PACK / raw


def cmd_uml(args: dict) -> dict:
    """Query or mutate a uml model.json through the umlmodel tool.

    One op per call. The tool loads, validates, applies the op, validates again,
    then writes atomically. `swarm.help({tool:'uml'})` lists every op.
    """
    op = args.get("op")
    if not op:
        raise SwarmError("pass op; run op:'list' for every op")
    argv = [
        sys.executable,
        str(PACK / "tools" / "shared" / "umlmodel"),
        str(op),
        "--json",
    ]
    if args.get("model"):
        argv += ["--model", str(_uml_model_path(args["model"], args.get("subsystem")))]
    if args.get("dryRun"):
        argv.append("--dry-run")
    control = {"op", "model", "subsystem", "dryRun", "view", "limit"}
    payload = {key: value for key, value in args.items() if key not in control}
    if payload:
        argv += ["--args", json.dumps(payload)]
    code, out, err = _run(argv)
    result: dict = {}
    if out.strip():
        try:
            parsed = json.loads(out)
            if isinstance(parsed, dict):
                result = parsed
        except json.JSONDecodeError:
            result = {}
    if not result:
        return {
            "tool": "umlmodel",
            "model": args.get("model"),
            "op": op,
            "ok": False,
            "changed": False,
            "exit": code,
            "stdout": out.strip()[:500] or None,
            "error": (err.strip() or "umlmodel printed no JSON")[:500],
        }
    result.setdefault("tool", "umlmodel")
    result["exit"] = code
    if err.strip() and not result.get("message"):
        result["stderr"] = err.strip()[:500]
    return result


# --------------------------------------------------------------------------- #
# paging and composite gates
# --------------------------------------------------------------------------- #


def cmd_page(args: dict) -> dict:
    """Fetch a page of a saved handle (from a view:"all" call)."""
    paths = _paths()
    data = _load_handle(args["handle"], paths)
    rows = data["rows"]
    total = len(rows)
    offset = max(0, int(args.get("offset", 0)))
    limit = int(args.get("limit", 50))
    page = rows[offset : offset + limit] if limit > 0 else rows[offset:]
    return {
        "handle": args["handle"],
        "name": data.get("name"),
        "total": total,
        "offset": offset,
        "returned": len(page),
        "next": offset + len(page) if offset + len(page) < total else None,
        "items": page,
    }


def _checked(fn, args: dict, project) -> dict:
    """Run a sub-command and project it, or return a compact error."""
    try:
        return project(fn(dict(args)))
    except Exception as error:  # noqa: BLE001  # one error per check, never a raise
        return {"error": f"{type(error).__name__}: {error}"}


def cmd_gate(args: dict) -> dict:
    """The terminal gate in one call: dry + ruff + format + pytest + acceptance.

    Returns one compact verdict for each requested check, plus `pass`.
    checks defaults to all five. Example: swarm.gate({subsystem, feature})
    """
    checks = args.get("checks") or ["dry", "ruff", "format", "pytest", "acceptance"]
    out: dict = {}
    if "dry" in checks:
        out["dry"] = _checked(cmd_dry, args, lambda r: {"total": r.get("total", 0)})
    if "ruff" in checks:
        out["ruff"] = _checked(
            cmd_ruff,
            args,
            lambda r: {"total": r.get("total", 0), "byCode": r.get("byCode", {})},
        )
    if "format" in checks:
        out["format"] = _checked(
            cmd_format, args, lambda r: {"total": r.get("total", 0)}
        )
    if "pytest" in checks:
        out["pytest"] = _checked(
            cmd_pytest,
            args,
            lambda r: {
                "passed": r.get("passed", 0),
                "failed": r.get("failed", 0),
                "failures": [f["test"] for f in r.get("failures", [])],
            },
        )
    if "acceptance" in checks:
        out["acceptance"] = _checked(
            cmd_acceptance,
            args,
            lambda r: {
                "passed": r.get("passed", 0),
                "failed": r.get("failed", 0),
                "failures": [f["test"] for f in r.get("failures", [])],
            },
        )
    ok = all(
        isinstance(v, dict)
        and not v.get("error")
        and not v.get("failed")
        and not v.get("total")
        for v in out.values()
    )
    out["pass"] = ok
    return out


def cmd_ready(args: dict) -> dict:
    """The record gate in one call: check + lint-record + decisions.

    checks defaults to all three. Example: swarm.ready({role:"architect", subsystem})
    """
    checks = args.get("checks") or ["check", "record", "decisions"]
    out: dict = {}
    if "check" in checks:
        out["check"] = _checked(
            cmd_check,
            args,
            lambda r: {
                "passed": r.get("passed"),
                "errors": r.get("errors"),
                "warnings": r.get("warnings"),
                "byCode": r.get("byCode", {}),
            },
        )
    if "record" in checks:
        out["record"] = _checked(
            cmd_lint_record,
            args,
            lambda r: {
                "passed": r.get("passed"),
                "errors": r.get("errors"),
                "warnings": r.get("warnings"),
            },
        )
    if "decisions" in checks:
        out["decisions"] = _checked(
            cmd_decisions, args, lambda r: {"open": r.get("open", 0)}
        )
    values = [v for v in out.values() if isinstance(v, dict) and not v.get("error")]
    out["pass"] = (
        all(v.get("passed") is not False for v in values)
        and out.get("decisions", {}).get("open", 0) == 0
    )
    return out


def _write_union_skeleton(root, subsystem: str, counts: dict):
    """Project the subsystem `SKELETON.md` from the module skeletons.

    One home for the contracts: `modules/<module>/SKELETON.md`. This file is a
    generated concatenation of those files, plus the cross-module brief of the
    critic. A hand copy of a contract drifts, so no role retypes one.

    A HAND-WRITTEN union is never overwritten. It carries the critic's cross-module
    synthesis, which the projection does not rebuild, so a blind overwrite would lose
    it. The projection claims the file only when it is absent or already generated.
    """
    out_path = root / "SKELETON.md"
    if out_path.is_file():
        existing = out_path.read_text(encoding="utf-8")
        if "GENERATED by swarm.genRecord" not in existing:
            return None  # a hand-written union stands; the critic owns it
    mod_root = root / "modules"
    if not mod_root.is_dir():
        return None
    mods = sorted(
        p for p in mod_root.iterdir() if p.is_dir() and (p / "SKELETON.md").is_file()
    )
    if not mods:
        return None
    brief_path = root / "04-critic" / "3-skeleton.md"
    brief = (
        brief_path.read_text(encoding="utf-8").strip() if brief_path.is_file() else ""
    )
    body = [
        f"# SKELETON — {subsystem}",
        "",
        "<!-- GENERATED by swarm.genRecord from the module skeletons. Do not hand-edit. -->",
        "",
        "The whole brief for the coder and the refactorer. The contracts live once, in",
        "`modules/<module>/SKELETON.md`, and this file concatenates them. The critic's",
        "cross-module brief is `04-critic/3-skeleton.md`.",
        "",
        f"- modules: {', '.join(p.name for p in mods)}",
        f"- interfaces: design/subsystems/{subsystem}/interfaces/<module>.md",
        (
            f"- counts: {counts['classes']} classes, {counts['ops']} ops,"
            f" {counts['edges']} edges (see COUNTS.md)"
        ),
        "- contract table: CONTRACTS.md",
        "- cross-module sections: the architect's structure and module map, and",
        "  the critic's review, economy, and decisions sections",
        "",
    ]
    if brief:
        body += ["## The critic's cross-module brief", "", brief, ""]
    for mod in mods:
        text = (mod / "SKELETON.md").read_text(encoding="utf-8").strip()
        body += [f"## MODULE — {mod.name}", "", text, ""]
    out = root / "SKELETON.md"
    out.write_text("\n".join(body), encoding="utf-8")
    return out


def cmd_gen_record(args: dict) -> dict:
    """Generate the record counts from `model.json`, so no hand count exists.

    Writes `design/subsystems/<subsystem>/COUNTS.md` and returns the counts. The
    record cites that file for its numbers; no role re-derives a count by hand.
    It also writes `CONTRACTS.md`, and projects `SKELETON.md` from the module
    skeletons when the subsystem has split into modules.
    """
    subsystem = args.get("subsystem")
    if not subsystem:
        raise SwarmError("pass subsystem")
    root = PACK / "design" / "subsystems" / str(subsystem)
    model_path = root / "model.json"
    if not model_path.exists():
        raise SwarmError(f"no model.json at {_short(model_path)}")
    model = json.loads(model_path.read_text(encoding="utf-8"))
    classes = [
        cls for pkg in model.get("packages", []) for cls in pkg.get("classes", [])
    ]
    ops = [op for cls in classes for op in cls.get("ops", [])]

    def is_command(op) -> bool:
        cqs = (op.get("annotations") or {}).get("cqs") or "query"
        return str(cqs).lower() == "command"

    commands = [op for op in ops if is_command(op)]
    queries = [op for op in ops if not is_command(op)]
    counts = {
        "classes": len(classes),
        "ops": len(ops),
        "commands": len(commands),
        "queries": len(queries),
        "edges": len(model.get("edges", [])),
        "levels": len(model.get("levels", [])),
    }
    body = [
        f"# COUNTS — {subsystem}",
        "",
        "Generated by `swarm.genRecord`. Do not hand-edit. Cite this file for the",
        "counts. A hand count drifts.",
        "",
        "| count | value |",
        "|---|---|",
        f"| classes | {counts['classes']} |",
        f"| ops | {counts['ops']} |",
        f"| commands | {counts['commands']} |",
        f"| queries | {counts['queries']} |",
        f"| edges | {counts['edges']} |",
        f"| levels | {counts['levels']} |",
        "",
    ]
    out = root / "COUNTS.md"
    out.write_text("\n".join(body), encoding="utf-8")

    contract_rows = []
    for cls in classes:
        cname = cls.get("name") or cls.get("id") or "?"
        for op in cls.get("ops", []):
            ann = op.get("annotations") or {}
            cqs = str(ann.get("cqs") or "query").lower()
            sig = (op.get("text") or op.get("name") or "?").replace("|", "\\|")
            pre = (ann.get("pre") or "-").replace("|", "\\|")
            post = (ann.get("post") or "-").replace("|", "\\|")
            inv = (ann.get("invariant") or "-").replace("|", "\\|")
            contract_rows.append(
                f"| `{cname}.{sig}` | {cqs} | {pre} | {post} | {inv} |"
            )
    contracts = [
        f"# CONTRACTS — {subsystem}",
        "",
        "Generated by `swarm.genRecord` from `model.json`. Do not hand-edit. The",
        "record cites this file for the contract table. A hand copy drifts.",
        "",
        "| method | CQS | pre | post | invariant |",
        "|---|---|---|---|---|",
        *contract_rows,
        "",
    ]
    contracts_out = root / "CONTRACTS.md"
    contracts_out.write_text("\n".join(contracts), encoding="utf-8")

    skeleton_out = _write_union_skeleton(root, str(subsystem), counts)
    result = {
        "subsystem": subsystem,
        "path": _short(out),
        "contracts": _short(contracts_out),
        "skeleton": _short(skeleton_out) if skeleton_out else None,
        **counts,
    }
    if skeleton_out is None:
        union = root / "SKELETON.md"
        if union.is_file():
            result["skeleton"] = _short(union)
            result["note"] = (
                "the union SKELETON.md is the critic's; genRecord left it alone. "
                "Write the cross-module brief in 04-critic/3-skeleton.md, then delete "
                "SKELETON.md to let the projection claim it."
            )
    return result


def cmd_report(args: dict) -> dict:
    """Report the session cost per role, from the OpenCode database.

    Reads `~/.local/share/opencode/opencode.db`. No new store. The rework count
    is the number of sessions per role past the first for one subsystem.
    """
    db = Path(
        os.environ.get(
            "OPENCODE_DB", Path.home() / ".local" / "share" / "opencode" / "opencode.db"
        )
    )
    if not db.exists():
        raise SwarmError(f"no OpenCode database at {db}")
    con = sqlite3.connect(str(db))
    table = "session_v2" if _table_exists(con, "session_v2") else "session"
    rows = con.execute(
        f"select agent, tokens_output, tokens_reasoning, time_created, time_updated from {table} "
        "where agent is not null order by time_created desc limit 400"
    ).fetchall()
    con.close()
    agg: dict = {}
    for agent, out_tok, reason_tok, tc, tu in rows:
        entry = agg.setdefault(
            str(agent), {"out": 0, "reason": 0, "sessions": 0, "minutes": 0.0}
        )
        entry["out"] += out_tok or 0
        entry["reason"] += reason_tok or 0
        entry["sessions"] += 1
        entry["minutes"] += max(0.0, ((tu or tc) - tc) / 60000.0)
    for entry in agg.values():
        entry["minutes"] = round(entry["minutes"], 1)
    return {"db": _short(db), "roles": agg}


def _table_exists(con, name: str) -> bool:
    return (
        con.execute(
            "select 1 from sqlite_master where type='table' and name=?", (name,)
        ).fetchone()
        is not None
    )


def cmd_triage(args: dict) -> dict:
    """A fast read-only snapshot: status + ruff + decisions.

    checks may add "pytest" or "check". Example: swarm.triage({subsystem})
    """
    checks = args.get("checks") or ["status", "ruff", "decisions"]
    out: dict = {}
    if "status" in checks:
        out["status"] = _checked(
            cmd_status,
            args,
            lambda r: {"lane": r.get("lane"), "missing": r.get("missing", [])},
        )
    if "ruff" in checks:
        out["ruff"] = _checked(
            cmd_ruff,
            args,
            lambda r: {"total": r.get("total", 0), "byCode": r.get("byCode", {})},
        )
    if "decisions" in checks:
        out["decisions"] = _checked(
            cmd_decisions,
            {**args, "role": args.get("role") or "interrogator"},
            lambda r: {"open": r.get("open", 0)},
        )
    if "pytest" in checks:
        out["pytest"] = _checked(
            cmd_pytest,
            args,
            lambda r: {"failed": r.get("failed", 0), "passed": r.get("passed", 0)},
        )
    if "check" in checks:
        out["check"] = _checked(
            cmd_check,
            args,
            lambda r: {"passed": r.get("passed"), "byCode": r.get("byCode", {})},
        )
    return out


# --------------------------------------------------------------------------- #
# catalog and help
# --------------------------------------------------------------------------- #


def _tool(
    name, group, replaces, summary, params, returns, example, output, notes="", roles=""
):
    """One tool's help entry. `params` is a list of (name, type, default, desc)."""
    return {
        "name": name,
        "group": group,
        "replaces": replaces,
        "roles": roles,
        "summary": summary,
        "params": [
            {"name": n, "type": t, "default": d, "desc": desc}
            for n, t, d, desc in params
        ],
        "returns": returns,
        "example": example,
        "output": output,
        "notes": notes,
    }


_M = (
    "subsystem",
    "string",
    "-",
    "The lane. Sets SWARM_LANE; the same string as the record id.",
)
_R = (
    "role",
    "string",
    "-",
    "interrogator | architect | designer | critic | specifier | coder | test-reviewer | refactorer | hotfixer.",
)
_VIEW = (
    "view",
    "summary|rows|all",
    "summary",
    "summary = counts. rows = inline cols+rows (limit). all = a paging handle.",
)
_LIMIT = ("limit", "int", "50", "Max rows when view is rows.")
_UML_OPS_HELP = None


def _uml_ops_help() -> dict | None:
    """The uml op catalog, read from the tool so the help never drifts."""
    global _UML_OPS_HELP
    if _UML_OPS_HELP is None:
        try:
            from umlmodel.ops import entry

            _UML_OPS_HELP = entry()
        except Exception:  # noqa: BLE001  # the catalog must not break over one tool's help
            _UML_OPS_HELP = {}
    return _UML_OPS_HELP or None


def _with_uml_help(tool: dict) -> dict:
    """Add the per-op usage to the uml tool's help entry."""
    entry = _uml_ops_help()
    if entry:
        tool["ops"] = entry["ops"]
        tool["invariants"] = entry["invariants"]
    return tool


TOOLS = [
    _tool(
        "status",
        "resolve",
        "harness.py status",
        "Resolve every configured root and the active lane.",
        [("wiring", "bool", "false", "Also return the full wiring map (large).")],
        "{lane, roots:{LABEL:path}, missing:[LABEL]}",
        "swarm.status()",
        {"lane": None, "roots": {"PACK": "swarm-forge-lite"}, "missing": ["LANE"]},
        "Resolve the roots first, with your subsystem, so the lane scopes them. wiring:true adds every absolute path.",
        "all",
    ),
    _tool(
        "modules",
        "resolve",
        "-",
        "The module map, the frozen interfaces, and the module layout of a subsystem.",
        [_M],
        "{subsystem, architecture, interfaces:[{id,path}], modules:[{id,design,skeleton}], split_ready}",
        "swarm.modules({subsystem:'clip'})",
        {
            "subsystem": "clip",
            "architecture": "design/subsystems/clip/02-architect/ARCHITECTURE.md",
            "interfaces": [
                {
                    "id": "engine-read-view",
                    "path": "design/subsystems/clip/interfaces/engine-read-view.md",
                }
            ],
            "modules": [{"id": "engine-read-view", "design": True, "skeleton": False}],
            "split_ready": True,
        },
        "Use it to split the designers: the modules with their skeletons, and the frozen interfaces.",
        "orchestrator, critic",
    ),
    _tool(
        "interface",
        "resolve",
        "-",
        "The frozen interface text of one module.",
        [_M, ("module", "string", "-", "The module id (required).")],
        "{subsystem, module, path, text}",
        "swarm.interface({subsystem:'clip',module:'engine-read-view'})",
        {
            "module": "engine-read-view",
            "path": "design/subsystems/clip/interfaces/engine-read-view.md",
            "text": "INTERFACE engine-read-view ...",
        },
        "Read the frozen interface of a module before you design or critique it. Only the architect edits it.",
        "orchestrator, designer, critic",
    ),
    _tool(
        "goal",
        "resolve",
        "-",
        "Read, or write, the orchestrator's scratchpad (design/subsystems/<subsystem>/GOAL.md).",
        [_M, ("text", "string", "-", "The new scratchpad text. Omit to read.")],
        "{subsystem, path, exists, text}",
        "swarm.goal({subsystem:'clip'})  ·  swarm.goal({subsystem:'clip',text:'# GOAL ...'})",
        {
            "subsystem": "clip",
            "path": "design/subsystems/clip/GOAL.md",
            "exists": True,
            "text": "# GOAL — clip ...",
        },
        "The orchestrator's scratchpad. Write the pipeline state here, and read it first on a resume.",
        "orchestrator",
    ),
    _tool(
        "envelope",
        "resolve",
        "harness.py envelope",
        "The dispatch fields, the ENV lines, and the stop-test line of a role.",
        [_R, _M],
        "{fields, env, stop_test, text}",
        "swarm.envelope({role:'coder',subsystem:'clip'})",
        {"fields": {"PACK": "...", "ROLE": "coder"}, "stop_test": "..."},
        "The orchestrator runs it and pastes text verbatim into the subagent prompt. Never compact it.",
        "orchestrator",
    ),
    _tool(
        "guide",
        "method",
        "harness.py guide",
        "The form file names, titles, and stop test of a role. Compact.",
        [
            _R,
            _M,
            (
                "items",
                "bool",
                "false",
                "Also return the instrument and rule of every item.",
            ),
        ],
        "{role, work, forms:[{file,title,order}], stop_test}",
        "swarm.guide({role:'architect',subsystem:'clip'})",
        {
            "role": "architect",
            "forms": [{"file": "2-crc-cards.md", "title": "2. CRC CARDS"}],
        },
        "The method map of one role: its forms, its stop test, and the fetch hint. forms gives the names alone.",
        "interrogator, specifier",
    ),
    _tool(
        "forms",
        "method",
        "harness.py guide",
        "Just the form file names and titles of a role. The smallest method map.",
        [_R],
        "{role, forms:[{file,title}], stop_test}",
        "swarm.forms({role:'architect'})",
        {"role": "architect", "forms": [{"file": "2-crc-cards.md"}]},
        "The smallest map: the form file names and titles of one role.",
        "interrogator, design team",
    ),
    _tool(
        "form",
        "method",
        "harness.py guide",
        "One form's items, with the instrument and rule of each.",
        [_R, ("file", "string", "-", "The form file name (required).")],
        "{role, file, title, items:[{id,kind,instrument,rule}]}",
        "swarm.form({role:'interrogator',file:'7-requirements.md'})",
        {
            "file": "7-requirements.md",
            "items": [{"id": "7-requirements.rows", "rule": "..."}],
        },
        "One form. The interrogator gets its items; every other role gets the template text.",
        "interrogator, design team",
    ),
    _tool(
        "fix",
        "method",
        "record.HINTS",
        "The one-line fix for a finding code (or every code when none is given).",
        [
            ("code", "string", "-", "One finding code."),
            ("codes", "string[]", "-", "Several finding codes."),
        ],
        "{code, fix} or {fixes:[...]}",
        "swarm.fix({code:'fit-missing'})",
        {"code": "fit-missing", "fix": "give Scale, Meter and Target"},
        "The one-line fix for a finding code. Ask for one code, or with none, for every code.",
        "interrogator, specifier, design team",
    ),
    _tool(
        "check",
        "record",
        "harness.py check",
        "Lint the record a role wrote, and write its computed stop test.",
        [
            _R,
            _M,
            ("work", "string", "-", "Override the work directory."),
            _VIEW,
            _LIMIT,
        ],
        "{passed, errors, warnings, byCode, stop_test} + cols/rows on view:rows",
        "swarm.check({role:'architect',subsystem:'clip'})",
        {"passed": False, "errors": 2, "byCode": {"fit-missing": 1, "rn-missing": 1}},
        "Lint the record you wrote and write your stop test. The design-role edit loop: fix a finding, call it again.",
        "interrogator, specifier, design team",
    ),
    _tool(
        "lintRecord",
        "record",
        "harness.py lint-record",
        "Lint the accepted subsystem record.",
        [
            _M,
            ("record", "string", "-", "Override the record directory."),
            ("specs", "string", "-", "Override the specs root."),
            _VIEW,
            _LIMIT,
        ],
        "{passed, errors, warnings, byCode} + cols/rows on view:rows",
        "swarm.lintRecord({subsystem:'clip'})",
        {"passed": True, "errors": 0, "warnings": 1},
        "The whole accepted record, every role. Run it before you hand the record on.",
        "interrogator, specifier, architect, critic, hotfixer",
    ),
    _tool(
        "genDoc",
        "record",
        "harness.py gen-doc",
        "Sync the requirement document to the record, in place, keyed by id.",
        [
            _M,
            ("record", "string", "-", "Override the record directory."),
            ("specs", "string", "-", "Override the specs root."),
            (
                "grow",
                "boolean",
                "false",
                "Append the rows the document lacks, at the end. The only way a document grows.",
            ),
        ],
        "{subsystem, document, rows, changed, absent}",
        "swarm.genDoc({subsystem:'clip'})",
        {
            "subsystem": "clip",
            "document": "docs/specs/09-clip.md",
            "rows": 9,
            "changed": True,
            "absent": [],
        },
        "The document is a VIEW of the record. It rewrites each row the document already carries, with the RECORD'S id and wording, and every other line stays. An id with no row is REPORTED and never written. Run it after you edit a requirement table.",
        "interrogator, hotfixer",
    ),
    _tool(
        "decisions",
        "record",
        "harness.py decisions",
        "The DECISION ledger. Default: the OPEN rows only (what the gate needs).",
        [
            _R,
            _M,
            ("work", "string", "-", "Override the work directory."),
            ("all", "bool", "false", "Include answered rows."),
        ],
        "{open, total, rows:[{id,status,question,options,answer}]}",
        "swarm.decisions({role:'interrogator',subsystem:'clip'})",
        {
            "open": 1,
            "total": 13,
            "rows": [
                {"id": "D4", "status": "open", "question": "...", "options": "..."}
            ],
        },
        "Feed the operator gate. all:true returns every row, not only the open ones.",
        "orchestrator, interrogator",
    ),
    _tool(
        "initWork",
        "record",
        "harness.py init-work",
        "Write a role's empty self-teaching forms to a NEW subsystem's record directory.",
        [
            _R,
            _M,
            ("work", "string", "-", "Override the work directory."),
            ("force", "bool", "false", "Reset an existing record (destructive)."),
        ],
        "{role, work, written:[file]|copied}",
        "swarm.initWork({role:'architect',subsystem:'clip'})",
        {"work": "design/subsystems/clip/02-architect", "written": ["2-crc-cards.md"]},
        "Write a role's empty forms for a NEW subsystem. It refuses when the record exists, unless force:true.",
        "interrogator, design team",
    ),
    _tool(
        "clean",
        "record",
        "harness.py clean",
        "Clear a disposable root of the active lane.",
        [("target", "hot|state|artifacts|all", "hot", "Which root to clear."), _M],
        "{target, cleared:[{label,path,removed}]}",
        "swarm.clean({target:'hot',subsystem:'clip'})",
        {"target": "hot", "cleared": [{"label": "hot", "removed": 3}]},
        "Drop one lane's disposable roots at a subsystem switch. It never touches the record or a persistent test.",
        "orchestrator",
    ),
    _tool(
        "checkEnvelope",
        "record",
        "harness.py check-envelope",
        "Lint a dispatch envelope: the duplicate-block rule and the cite hint. No size limit.",
        [
            ("text", "string", "-", "The envelope text."),
            ("file", "string", "-", "Or a file that holds it."),
        ],
        "{pass, repeated, env_twice, long_lines, has_cite, hint}",
        "swarm.checkEnvelope({text: envelopeText})",
        {
            "pass": True,
            "repeated": [],
            "env_twice": False,
            "long_lines": 0,
            "has_cite": True,
            "hint": None,
        },
        "Run it on a dispatch before you send it: the duplicate-block rule and the cite hint.",
        "orchestrator",
    ),
    _tool(
        "vocabRename",
        "record",
        "harness.py vocab-rename",
        "Bulk rename a token across files, with counts and an optional verify pass.",
        [
            ("old", "string", "-", "The token to replace (required)."),
            ("new", "string", "-", "The replacement (required)."),
            ("files", "string[]", "-", "Files or directories (required)."),
            ("word", "bool", "false", "Whole-word match only."),
            ("dryRun", "bool", "false", "Report the hits without writing."),
            ("verify", "bool", "false", "Fail when any occurrence remains."),
        ],
        "{total, files, verified}",
        "swarm.vocabRename({old:'oldname',new:'newname',files:['design/subsystems/clip'],dryRun:true})",
        {"total": 59, "files": [{"file": "20-goal.md", "count": 3}]},
        "One token, whole-word, across the files you name. Run dryRun first, then verify.",
        "orchestrator",
    ),
    _tool(
        "ruff",
        "quality",
        "ruff4py",
        "Ruff findings, without the annotated source frames.",
        [
            (
                "paths",
                "string[]",
                "source + persistent roots",
                "Files or dirs to lint.",
            ),
            _M,
            _VIEW,
            _LIMIT,
        ],
        "{total, byCode} + cols/rows on view:rows + handle on view:all",
        "swarm.ruff({paths:['<source_root>']})",
        {"tool": "ruff", "total": 6, "byCode": {"UP035": 2, "UP007": 2, "UP037": 2}},
        "Structured findings, without the source frames. A clean tree reports 0.",
        "coder, refactorer, hotfixer",
    ),
    _tool(
        "dry",
        "quality",
        "dryer",
        "Duplicate-code pairs (dryer).",
        [
            ("paths", "string[]", "source roots", "Files or dirs to scan."),
            ("minLines", "int", "4", "Minimum candidate size in lines."),
            ("minNodes", "int", "20", "Minimum normalized syntax nodes."),
            ("threshold", "number", "0.82", "Minimum structural similarity score."),
            _M,
            _VIEW,
            _LIMIT,
        ],
        "{total} + pairs on view:rows + handle on view:all",
        "swarm.dry({paths:['<source_root>']})",
        {"tool": "dryer", "total": 2, "pairs": [["a.py:449-457", "b.py:433-441"]]},
        "Duplicate-code pairs (dryer). Scope paths to the area you changed.",
        "coder, refactorer",
    ),
    _tool(
        "pytest",
        "quality",
        "pytest",
        "Run pytest and return counts and failing tests, not the whole log.",
        [
            _M,
            ("k", "string", "-", "A pytest -k expression."),
            ("paths", "string[]", "-", "Test paths relative to the persistent root."),
            (
                "scope",
                "scoped|full",
                "full when unscoped",
                "full runs the whole suite.",
            ),
        ],
        "{passed, failed, errors, skipped, failures:[{test,reason}], summary, exit}",
        "swarm.pytest({k:'privacy',subsystem:'clip'})",
        {"passed": 97, "failed": 0, "summary": "97 passed in 2.5s"},
        "Counts and failing tests, not the whole log. Scope it with k or paths while you work, and run the full suite once, at the terminal gate.",
        "coder, test-reviewer, refactorer, hotfixer",
    ),
    _tool(
        "crap",
        "quality",
        "crapper",
        "CRAP (complexity x coverage), worst first. Default: only the rows above CRAP 10.",
        [
            _M,
            (
                "filters",
                "string[]",
                "-",
                "Only report functions whose namespace contains a fragment.",
            ),
            ("sourceRoot", "string[]", "-", "Override the source roots."),
            (
                "reuseFresh",
                "bool",
                "false",
                "Reuse a fresh coverage report instead of running the tests.",
            ),
            (
                "useExisting",
                "bool",
                "false",
                "Read the coverage report without a test run.",
            ),
            (
                "all",
                "bool",
                "false",
                "Return every row, not just those above the threshold.",
            ),
        ],
        "{total, above, threshold, rows:[{function,namespace,cc,coverage,crap}]}",
        "swarm.crap({reuseFresh:true,subsystem:'clip'})",
        {"total": 53, "above": 0, "threshold": 10.0, "rows": []},
        "CRAP, worst first, from the vendored crapper at the pack's CRAP 10 threshold. A coverage run is slow, so reuseFresh:true skips it when the report is newer than every source and test.",
        "coder, refactorer",
    ),
    _tool(
        "acceptance",
        "quality",
        "run_acceptance.py",
        "Run the acceptance pipeline (parse, dry-check, generate, run).",
        [("feature", "string", "*", "A feature stem, or '*' for every feature."), _M],
        "{features, passed, failed, failures, summary, exit}",
        "swarm.acceptance({feature:'privacy_recording'})",
        {"features": ["privacy_recording"], "passed": 27, "failed": 0},
        "Parse, dry-check, generate and run the acceptance for a feature. Name the feature stem; '*' runs every feature.",
        "coder, refactorer, hotfixer",
    ),
    _tool(
        "gherkinParse",
        "gherkin",
        "gherkin-parser",
        "Parse a .feature file to the JSON IR and summarize it.",
        [
            ("feature", "string", "-", "The feature stem (required)."),
            _M,
            ("names", "bool", "false", "Include the scenario names."),
        ],
        "{feature, ir, scenario_count, exit}",
        "swarm.gherkinParse({feature:'privacy_recording'})",
        {"scenario_count": 23, "ir": "dump/privacy_recording.json"},
        "Pass the feature STEM: no path, no .feature. It writes the JSON IR under the artifacts root.",
        "specifier",
    ),
    _tool(
        "gherkinDry",
        "gherkin",
        "ir-dry-checker",
        "Dry-check the IR and summarize the report.",
        [
            (
                "ir",
                "string",
                "-",
                "The IR path, or its name under the artifacts root (required).",
            ),
            ("includeExact", "bool", "false", "Also report exact duplicates."),
            _M,
            _VIEW,
            _LIMIT,
        ],
        "{counts, total} + findings on view:rows",
        "swarm.gherkinDry({ir:'privacy_recording.json'})",
        {"counts": {"near-duplicate": 25, "possible-synonym": 79}, "total": 104},
        "Run it on the ir that gherkinParse returned, or on the bare name.",
        "specifier",
    ),
    _tool(
        "umlRender",
        "uml",
        "render.py",
        "Render model.json to a standalone model.html.",
        [
            (
                "model",
                "string",
                "-",
                "The model.json path, or its name under the subsystem record (required).",
            ),
            _M,
            ("out", "string", "-", "Output HTML path."),
            ("check", "bool", "false", "Flag model errors."),
        ],
        "{model, exit, stdout}",
        "swarm.umlRender({model:'model.json',subsystem:'clip',check:true})",
        {"model": ".../model.json", "exit": 0, "stdout": "wrote ... (0 violations)"},
        "Render model.json to model.html. The output is one line and a file, so it is never compacted.",
        "architect, critic, refactorer",
    ),
    _tool(
        "umlSync",
        "uml",
        "sync_python.py",
        "Overlay the real signatures and CRAP metrics onto the model.",
        [
            (
                "model",
                "string",
                "-",
                "The model.json path, or its name under the subsystem record (required).",
            ),
            _M,
            ("source", "string", "first source root", "Source root to scan."),
            ("crap", "string", "-", "A crapper report to read metrics from."),
            ("out", "string", "-", "Output path."),
        ],
        "{model, exit, stdout}",
        "swarm.umlSync({model:'model.json',subsystem:'clip'})",
        {"exit": 0, "stdout": "wrote .../model.live.json (19 matched, 0 missing)"},
        "Overlay the real signatures and the CRAP metrics. It writes model.live.json, never model.json.",
        "refactorer",
    ),
    _tool(
        "umlScan",
        "uml",
        "scan_python.py",
        "Scan a Python source root into a model.json.",
        [
            ("root", "string", "-", "The source root to scan (required)."),
            ("prefix", "string", "-", "Only include classes under this prefix."),
            ("out", "string", "-", "Output path."),
            ("title", "string", "-", "Model title."),
        ],
        "{root, exit, stdout}",
        "swarm.umlScan({root:'<source_root>'})",
        {"exit": 0, "stdout": "wrote ... (2 packages, 143 subsystems)"},
        "A bootstrap: scan an existing source root into a model.json. The output lands under the artifacts root.",
        "architect",
    ),
    _with_uml_help(
        _tool(
            "uml",
            "uml",
            "umlmodel",
            "Query or mutate a uml model.json: classes, packages, levels, edges, violations, and every edit. One op per call.",
            [
                (
                    "op",
                    "string",
                    "-",
                    "The operation. Run op:'list' for every op, or swarm.help({tool:'uml'}) for the full usage.",
                ),
                (
                    "model",
                    "string",
                    "-",
                    "The model.json path, or its name under the subsystem record.",
                ),
                (
                    "dryRun",
                    "bool",
                    "false",
                    "Print the diff and write nothing.",
                ),
            ],
            "{model, op, ok, changed, exit, stdout} + the row data of a query",
            "swarm.uml({op:'violations',model:'design/subsystems/safety-rule-engine/model.json'})",
            {
                "op": "violations",
                "ok": True,
                "changed": False,
                "exit": 0,
                "count": 0,
                "rows": [],
            },
            "One op runs per call: load, validate, apply, validate, then write atomically. "
            "A rejected op returns ok:false with a message and writes nothing. "
            "Any other key is an op param; run op:'list' to discover them.",
            "architect, critic, refactorer",
        )
    ),
    _tool(
        "page",
        "aggregate",
        "list tools",
        "Fetch a page of a saved handle (from a view:'all' call).",
        [
            ("handle", "string", "-", "The handle id (required)."),
            ("offset", "int", "0", "Start row."),
            ("limit", "int", "50", "Rows per page; 0 = the rest."),
        ],
        "{handle, name, total, offset, returned, next, items}",
        "swarm.page({handle:'abc123',offset:50})",
        {"total": 104, "offset": 50, "returned": 50, "next": 100, "items": ["..."]},
        "Fetch more rows for a handle from a view:'all' call. Loop until next is null.",
        "refactorer",
    ),
    _tool(
        "gate",
        "aggregate",
        "dry+ruff+format+pytest+acceptance",
        "The terminal gate in one call: dry + ruff + format + pytest + acceptance.",
        [
            _M,
            ("feature", "string", "*", "The acceptance feature stem, or '*' for all."),
            (
                "checks",
                "string[]",
                "all five",
                "Subset of ['dry','ruff','format','pytest','acceptance'].",
            ),
            ("k", "string", "-", "A pytest -k expression."),
            ("paths", "string[]", "-", "Pytest paths."),
            ("scope", "scoped|full", "-", "full runs the whole pytest suite."),
            ("reuseFresh", "bool", "false", "Reuse a fresh coverage.lcov."),
        ],
        "{dry, ruff, format, pytest, acceptance, pass}",
        "swarm.gate({subsystem:'clip',feature:'clip_recording'})",
        {
            "dry": {"total": 0},
            "ruff": {"total": 0},
            "format": {"total": 0},
            "pytest": {"failed": 0},
            "acceptance": {"failed": 0},
            "pass": True,
        },
        "The terminal gate in one call: dry, ruff, format, pytest and acceptance. checks selects a subset.",
        "refactorer, hotfixer",
    ),
    _tool(
        "ready",
        "aggregate",
        "check+lint-record+decisions",
        "The record gate in one call: check + lint-record + decisions.",
        [
            _R,
            _M,
            (
                "checks",
                "string[]",
                "all three",
                "Subset of ['check','record','decisions'].",
            ),
        ],
        "{check, record, decisions, pass}",
        "swarm.ready({role:'architect',subsystem:'clip'})",
        {
            "check": {"passed": True},
            "record": {"passed": True},
            "decisions": {"open": 0},
            "pass": True,
        },
        "The record gate in one call: check, lint-record, and the open decision count.",
        "interrogator, specifier, architect, critic, orchestrator",
    ),
    _tool(
        "triage",
        "aggregate",
        "status+ruff+decisions",
        "A fast read-only snapshot: status + ruff + decisions.",
        [
            _M,
            ("role", "string", "interrogator", "The role for the decisions check."),
            (
                "checks",
                "string[]",
                "status,ruff,decisions",
                "Subset of ['status','ruff','decisions','pytest','check'].",
            ),
        ],
        "{status, ruff, decisions}",
        "swarm.triage({subsystem:'clip'})",
        {
            "status": {"lane": "clip", "missing": []},
            "ruff": {"total": 0},
            "decisions": {"open": 0},
        },
        "A fast read-only snapshot. Use it before a dispatch.",
        "orchestrator",
    ),
    _tool(
        "genRecord",
        "record",
        "swarm_json.py genRecord",
        "Generate the record counts into COUNTS.md and CONTRACTS.md, and project SKELETON.md from the module skeletons. No hand count, no hand copy.",
        [_M],
        "{subsystem, path, classes, ops, commands, queries, edges, levels}",
        "swarm.genRecord({subsystem:'clip'})",
        {
            "subsystem": "clip",
            "path": "design/subsystems/clip/COUNTS.md",
            "classes": 43,
            "ops": 103,
            "commands": 12,
            "queries": 91,
            "edges": 101,
            "levels": 13,
        },
        "Run it after a model change. It writes COUNTS.md and CONTRACTS.md, and it never overwrites a hand-written union SKELETON.md.",
        "architect, critic",
    ),
    _tool(
        "report",
        "record",
        "swarm_json.py report",
        "Report the session cost per role from the OpenCode database: tokens, sessions, minutes.",
        [],
        "{db, roles:{role:{out,reason,sessions,minutes}}}",
        "swarm.report()",
        {
            "db": "opencode.db",
            "roles": {
                "coder": {"out": 147, "reason": 289, "sessions": 3, "minutes": 351.0}
            },
        },
        "Where the session time went: tokens, sessions and minutes for each role.",
        "orchestrator",
    ),
    _tool(
        "docs",
        "meta",
        "-",
        "The compact catalog: every tool with a summary and an example.",
        [],
        "{pack, backend, tools:[{command,summary,example}]}",
        "swarm.docs()",
        {"tools": [{"command": "ruff", "summary": "..."}]},
        "The catalog: every tool with a summary and an example. Then swarm.help({tool}) for one tool.",
        "orchestrator",
    ),
    _tool(
        "help",
        "meta",
        "-",
        "One tool's full help: params, defaults, return shape, example, output.",
        [("tool", "string", "-", "A tool name. With none, the whole catalog.")],
        "{name, group, summary, params:[{name,type,default,desc}], returns, example, output}",
        "swarm.help({tool:'ruff'})",
        {
            "name": "ruff",
            "params": [{"name": "view", "default": "summary"}],
            "example": "swarm.ruff({paths:[...]})",
        },
        "The full help of one tool: its params with defaults, its return shape, and an example.",
        "all",
    ),
]

BY_NAME = {t["name"]: t for t in TOOLS}
_GROUPS = [
    "resolve",
    "method",
    "record",
    "quality",
    "gherkin",
    "uml",
    "aggregate",
    "meta",
]


def cmd_docs(args: dict) -> dict:
    """The compact catalog: every tool with a summary and one example."""
    return {
        "pack": str(PACK),
        "backend": str(Path(__file__).resolve()),
        "backend_call": "python3 <pack>/tools/shared/swarm_json.py <command> '<json-args>'",
        "views": "List tools default to a summary. view:'rows' = inline cols+rows. view:'all' = a paging handle.",
        "next": "call swarm.help({tool:'ruff'}) for one tool's params and output",
        "tools": [
            {
                "command": t["name"],
                "group": t["group"],
                "summary": t["summary"],
                "example": t["example"],
            }
            for t in TOOLS
        ],
    }


def cmd_help(args: dict) -> dict:
    """One tool's full help. With no tool, the whole catalog."""
    name = args.get("tool") or args.get("name")
    if not name:
        return {
            "tools": [
                {
                    "name": t["name"],
                    "group": t["group"],
                    "replaces": t["replaces"],
                    "summary": t["summary"],
                }
                for t in TOOLS
            ],
            "hint": "call swarm.help({tool:'ruff'}) for one tool",
        }
    tool = BY_NAME.get(name)
    if tool is None:
        raise SwarmError(f"no tool {name!r}; known: {sorted(BY_NAME)}")
    return tool


def _help_text(name: str | None = None) -> str:
    """A plain-text usage page, for `python3 swarm_json.py --help`."""
    if name is None:
        lines = [
            "swarm_json -- the backend of the swarm.* Code Mode tools",
            "",
            "usage:",
            "  python3 swarm_json.py <command> '<json-args>'",
            "  python3 swarm_json.py <command> --help",
            "  python3 swarm_json.py --help",
            "",
            "The args JSON may carry subsystem=<name> to set the lane.",
        ]
        for group in _GROUPS:
            members = [t for t in TOOLS if t["group"] == group]
            if not members:
                continue
            lines.append("")
            lines.append(f"[{group}]")
            for t in members:
                lines.append(f"  {t['name']:<14} {t['summary']}")
        lines += [
            "",
            "The same catalog is `swarm.docs()` in Code Mode; one tool's detail is `swarm.help({tool})`.",
        ]
        return "\n".join(lines)
    tool = BY_NAME.get(name)
    if tool is None:
        return f"swarm_json: no tool {name!r}; known: {', '.join(sorted(BY_NAME))}"
    lines = [
        f"{tool['name']} -- {tool['summary']}",
        f"group: {tool['group']}    replaces: {tool['replaces']}    roles: {tool['roles'] or '-'}",
        "",
        "params:",
    ]
    if tool["params"]:
        for param in tool["params"]:
            lines.append(
                f"  {param['name']:<10} {param['type']:<22} default={param['default']:<26} {param['desc']}"
            )
    else:
        lines.append("  (none)")
    lines += [
        "",
        f"returns: {tool['returns']}",
        f"example: {tool['example']}",
        f"output:  {json.dumps(tool['output'], default=str)}",
    ]
    if tool["notes"]:
        lines.append(f"notes:   {tool['notes']}")
    if tool.get("ops"):
        lines += ["", f"ops ({len(tool['ops'])}):"]
        for item in tool["ops"]:
            params = ", ".join(param["name"] for param in item["params"]) or "-"
            lines.append(f"  {item['op']:<16} {item['kind']:<6} {item['purpose']}")
            lines.append(f"      params: {params}")
            lines.append(f"      e.g. {item['example']}")
        lines += ["", "invariants:"]
        lines += [f"  - {line}" for line in tool.get("invariants", [])]
    return "\n".join(lines)


COMMANDS = {
    "status": cmd_status,
    "modules": cmd_modules,
    "interface": cmd_interface,
    "goal": cmd_goal,
    "envelope": cmd_envelope,
    "guide": cmd_guide,
    "forms": cmd_forms,
    "form": cmd_form,
    "fix": cmd_fix,
    "check": cmd_check,
    "lint_record": cmd_lint_record,
    "decisions": cmd_decisions,
    "init_work": cmd_init_work,
    "clean": cmd_clean,
    "check_envelope": cmd_check_envelope,
    "vocab_rename": cmd_vocab_rename,
    "ruff": cmd_ruff,
    "dry": cmd_dry,
    "pytest": cmd_pytest,
    "crap": cmd_crap,
    "acceptance": cmd_acceptance,
    "gherkin_parse": cmd_gherkin_parse,
    "gherkin_dry": cmd_gherkin_dry,
    "uml_render": cmd_uml_render,
    "uml_sync": cmd_uml_sync,
    "uml_scan": cmd_uml_scan,
    "uml": cmd_uml,
    "page": cmd_page,
    "gate": cmd_gate,
    "ready": cmd_ready,
    "triage": cmd_triage,
    "genRecord": cmd_gen_record,
    "genDoc": cmd_gen_doc,
    "report": cmd_report,
    "docs": cmd_docs,
    "help": cmd_help,
}


def main(argv=None) -> int:
    argv = list(sys.argv if argv is None else argv)
    if len(argv) < 2:
        print(_help_text())
        return 0
    if argv[1] in ("-h", "--help"):
        print(_help_text(argv[2] if len(argv) > 2 else None))
        return 0
    if argv[1] == "help" and not (len(argv) > 2 and argv[2].lstrip().startswith("{")):
        print(_help_text(argv[2] if len(argv) > 2 else None))
        return 0
    if len(argv) > 2 and argv[2] in ("-h", "--help"):
        print(_help_text(argv[1]))
        return 0
    command = argv[1]
    raw = argv[2] if len(argv) > 2 else "{}"
    try:
        args = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError as error:
        print(json.dumps({"error": f"bad json args: {error}"}))
        return 0
    subsystem = args.get("subsystem")
    if subsystem:
        os.environ["SWARM_LANE"] = str(subsystem)
    handler = COMMANDS.get(command)
    if handler is None:
        print(
            json.dumps(
                {"error": f"unknown command: {command}", "known": sorted(COMMANDS)}
            )
        )
        return 0
    try:
        result = handler(args)
    except Exception as error:  # noqa: BLE001  # one JSON error object, never a traceback
        print(
            json.dumps(
                {"error": f"{type(error).__name__}: {error}", "command": command}
            )
        )
        return 0
    try:
        print(json.dumps(result, default=str))
    except BrokenPipeError:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
