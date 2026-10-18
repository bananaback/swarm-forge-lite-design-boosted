#!/usr/bin/env python3
import json
import os
import sqlite3
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PACK = HERE.parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(PACK / "tools" / "refactorer"))

from swarm_core import (
    cmd_check,
    cmd_decisions,
    cmd_lint_record,
)
from swarm_quality import cmd_dry, cmd_format, cmd_ruff
from swarm_support import (
    SwarmError,
    _short,
)
from swarm_test import cmd_acceptance, cmd_pytest

_WORKSPACE = PACK.parent


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
    if args.get("crap") and "crap" not in checks:
        checks = [*checks, "crap"]
    out: dict = {}

    def verdict(r: dict, counts: str) -> dict:
        """One check's compact result plus an explicit ok/exit verdict."""
        ok = not r.get("error") and int(r.get("exit", 0)) == 0
        if ok and counts != "exit":
            ok = int(r.get(counts, 0)) == 0
        return {**r, "ok": ok}

    if "dry" in checks:
        out["dry"] = _checked(
            cmd_dry,
            args,
            lambda r: verdict(
                {"total": r.get("total", 0), "exit": r.get("exit", 0)}, "total"
            ),
        )
    if "ruff" in checks:
        out["ruff"] = _checked(
            cmd_ruff,
            args,
            lambda r: verdict(
                {
                    "total": r.get("total", 0),
                    "byCode": r.get("byCode", {}),
                    "exit": r.get("exit", 0),
                },
                "total",
            ),
        )
    if "format" in checks:
        out["format"] = _checked(
            cmd_format,
            args,
            lambda r: verdict(
                {"total": r.get("total", 0), "exit": r.get("exit", 0)}, "total"
            ),
        )
    if "pytest" in checks:
        out["pytest"] = _checked(
            cmd_pytest,
            args,
            lambda r: verdict(
                {
                    "passed": r.get("passed", 0),
                    "failed": r.get("failed", 0),
                    "errors": r.get("errors", 0),
                    "exit": r.get("exit", 0),
                    "failures": [f["test"] for f in r.get("failures", [])],
                },
                "failed",
            ),
        )
    if "acceptance" in checks:
        out["acceptance"] = _checked(
            cmd_acceptance,
            args,
            lambda r: verdict(
                {
                    "passed": r.get("passed", 0),
                    "failed": r.get("failed", 0),
                    "exit": r.get("exit", 0),
                    "failures": [f["test"] for f in r.get("failures", [])],
                },
                "failed",
            ),
        )
    if "crap" in checks:
        from swarm_quality import cmd_crap

        out["crap"] = _checked(
            cmd_crap,
            args,
            lambda r: verdict(
                {"above": r.get("above", 0), "exit": r.get("exit", 0)}, "above"
            ),
        )
    out["pass"] = all(v.get("ok") for v in out.values() if isinstance(v, dict))
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
    checks_ok = all(
        isinstance(v, dict) and not v.get("error") and v.get("passed") is not False
        for v in out.values()
    )
    out["pass"] = checks_ok and out.get("decisions", {}).get("open", 0) == 0
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
    flat = sorted(p for p in mod_root.glob("*.md"))
    if not mods and not flat:
        return None
    brief_path = root / "04-critic" / "3-skeleton.md"
    brief = (
        brief_path.read_text(encoding="utf-8").strip() if brief_path.is_file() else ""
    )
    if not brief:
        review = root / "review.md"
        brief = review.read_text(encoding="utf-8").strip() if review.is_file() else ""
    names = [p.name for p in mods] + [p.stem for p in flat]
    body = [
        f"# SKELETON — {subsystem}",
        "",
        "<!-- GENERATED by swarm.genRecord from the module contracts. Do not hand-edit. -->",
        "",
        "The whole brief for the coder and the refactorer. The contracts live once, in",
        "`modules/<module>.md`. The frozen interface text is in `architecture.md`.",
        "",
        f"- modules: {', '.join(names)}",
        f"- interfaces: design/subsystems/{subsystem}/architecture.md",
        (
            f"- counts: {counts['classes']} classes, {counts['ops']} ops,"
            f" {counts['edges']} edges (from model.json)"
        ),
        "",
    ]
    if brief:
        body += ["## Cross-module brief", "", brief, ""]
    for mod in mods:
        text = (mod / "SKELETON.md").read_text(encoding="utf-8").strip()
        body += [f"## MODULE — {mod.name}", "", text, ""]
    for path in flat:
        body += [
            f"## MODULE — {path.stem}",
            "",
            path.read_text(encoding="utf-8").strip(),
            "",
        ]
    out = root / "SKELETON.md"
    out.write_text("\n".join(body), encoding="utf-8")
    return out


def cmd_gen_record(args: dict) -> dict:
    """Project `SKELETON.md` from the module contracts, and return model counts.

    Counts are returned as data, never written as a second document. The record
    keeps one copy of each contract: `modules/<module>.md`.
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
    skeleton_out = _write_union_skeleton(root, str(subsystem), counts)
    result = {
        "subsystem": subsystem,
        "model": _short(model_path),
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
