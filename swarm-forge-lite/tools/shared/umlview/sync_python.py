#!/usr/bin/env python3
"""umlview sync -- overlay the real implementation onto an accepted design model.

Reads the design model.json (the accepted skeleton) and a Python source root, and writes
``<stem>.live.json``. The overlay is additive and non-destructive: the accepted model.json
is never modified.

What the live model changes:

  - every op's signature (arg names/types and return) becomes the implementation's;
  - a method implemented but absent from the skeleton is appended (``op.live.status``
    = ``"new"``);
  - a skeleton method absent from the source is kept and flagged (``"missing"``);
  - a class with no match is flagged (``class.live.status`` = ``"missing"``) or, when two
    source classes share its name, ``"ambiguous"``;
  - a class's dataclass fields become the implementation's, when it declares any;
  - per-op ``op.metrics`` = ``{cc, coverage (0..1), crap}`` from a crapper report.

Every authored annotation (secret, core, responsibility, cqs, pre, post, invariant,
levels, edges) is carried over untouched. The top-level ``live`` block records the source
root, the report, and the match counts, so the viewer can show a LIVE badge.

Usage:
  sync_python.py MODEL.json --source SRC_ROOT [--crap CRAP.txt] [--out MODEL.live.json]

Point ``--source`` at the task's own subtree (e.g. ``app/pipeline/safety_check``) so a
class name that also appears in a sibling task is not ambiguous. Point the crapper run's
``--root`` at the same subtree, so every namespace matches. Produce the report with the
vendored ``crapper`` (its stdout), and render the result with ``render.py MODEL.live.json``.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from pathlib import Path

CRAP_ROW = re.compile(
    r"^(?P<name>\S+)\s+(?P<namespace>\S+)\s+"
    r"(?P<cc>\d+)\s+(?P<cov>\S+)\s+(?P<crap>\S+)\s*$"
)


def annotation_text(node) -> str | None:
    """The source text of a type annotation, or None."""
    if node is None:
        return None
    try:
        return ast.unparse(node)
    except Exception:  # noqa: BLE001  # an unparseable annotation yields no text
        return None


def source_of(node, lines: list) -> str:
    """The exact source lines of a function, decorators included."""
    start = node.lineno
    for decorator in getattr(node, "decorator_list", []):
        start = min(start, decorator.lineno)
    end = getattr(node, "end_lineno", start)
    return "\n".join(lines[start - 1 : end])


def _named(name: str, node) -> dict:
    """{name, type?} from an argument name and its annotation node."""
    out = {"name": name}
    text = annotation_text(node)
    if text:
        out["type"] = text
    return out


def argument(node) -> dict:
    """One op argument as {name, type?}; self/cls are dropped by the caller."""
    return _named(node.arg, node.annotation)


def arguments(fn) -> list:
    """The callable's arguments in source order, self/cls excluded."""
    spec = fn.args
    out = []
    for node in list(getattr(spec, "posonlyargs", [])) + list(spec.args):
        if node.arg not in ("self", "cls"):
            out.append(argument(node))
    if spec.vararg is not None:
        out.append(_named("*" + spec.vararg.arg, spec.vararg.annotation))
    for node in spec.kwonlyargs:
        out.append(argument(node))
    if spec.kwarg is not None:
        out.append(_named("**" + spec.kwarg.arg, spec.kwarg.annotation))
    return out


def scan_source(root: Path) -> dict:
    """{class name: [record]} for every class defined under root.

    A record is {module, path (relative), methods {name: signature}, fields [text]}.
    """
    index: dict = {}
    for path in sorted(root.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        try:
            tree = ast.parse(text)
        except SyntaxError:
            continue
        lines = text.splitlines()
        rel = path.relative_to(root)
        for node in tree.body:
            if not isinstance(node, ast.ClassDef):
                continue
            methods = {}
            fields = []
            for stmt in node.body:
                if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    sig = {
                        "name": stmt.name,
                        "args": arguments(stmt),
                        "lineno": stmt.lineno,
                        "code": source_of(stmt, lines),
                    }
                    returns = annotation_text(stmt.returns)
                    if returns:
                        sig["returns"] = returns
                    methods[stmt.name] = sig
                elif isinstance(stmt, ast.AnnAssign) and isinstance(
                    stmt.target, ast.Name
                ):
                    text = annotation_text(stmt.annotation)
                    fields.append(
                        {
                            "text": f"{stmt.target.id} : {text}"
                            if text
                            else stmt.target.id
                        }
                    )
            index.setdefault(node.name, []).append(
                {
                    "module": ".".join(rel.with_suffix("").parts),
                    "path": rel,
                    "methods": methods,
                    "fields": fields,
                }
            )
    return index


def parse_crap(path: Path) -> list:
    """The function rows of a crapper text report."""
    rows = []
    for line in path.read_text().splitlines():
        match = CRAP_ROW.match(line)
        if not match:
            continue
        cov = match.group("cov")
        crap = match.group("crap")
        rows.append(
            {
                "name": match.group("name"),
                "namespace": match.group("namespace"),
                "cc": int(match.group("cc")),
                "coverage": None if cov == "N/A" else float(cov.rstrip("%")) / 100.0,
                "crap": None if crap == "N/A" else float(crap),
            }
        )
    return rows


def choose_class(candidates: list, model_class: dict):
    """Pick the source class for a model class; None when absent or ambiguous.

    Disambiguates by the model id's first segment (e.g. ``core``/``shell``) matching a
    path component of the source module.
    """
    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0]
    segment = str(model_class.get("id", "")).split(".")[0].lower().replace("-", "_")
    preferred = [
        record
        for record in candidates
        if segment and segment in [part.lower() for part in record["path"].parts]
    ]
    return preferred[0] if len(preferred) == 1 else None


def metrics_for(class_name: str, signature: dict, rows_by_name: dict):
    """The crapper row for one method: same class and method name.

    crapper names a method ``<module>.<Class>``. The model classes live in their
    own subtree, so the module prefix may differ: match a namespace that ends
    with ``.<class_name>``, and fall back to the method name alone.
    """
    candidates = rows_by_name.get(signature["name"], [])
    if not candidates:
        return None
    suffix = "." + class_name
    for row in candidates:
        if row["namespace"] == class_name or row["namespace"].endswith(suffix):
            return row
    return candidates[0]


def attach_metrics(op: dict, row) -> bool:
    """Copy cc/coverage/crap from a report row onto op.metrics; True when set."""
    if row is None:
        return False
    metrics = op.setdefault("metrics", {})
    metrics["cc"] = row["cc"]
    if row["coverage"] is not None:
        metrics["coverage"] = round(row["coverage"], 4)
    if row["crap"] is not None:
        metrics["crap"] = round(row["crap"], 2)
    return True


def overlay(model: dict, index: dict, rows_by_name: dict) -> dict:
    """Overlay the source onto the model in place; return the match counts."""
    counts = {
        "matched": 0,
        "missing": 0,
        "ambiguous": 0,
        "ops_updated": 0,
        "ops_new": 0,
        "ops_missing": 0,
        "ops_measured": 0,
    }
    packages = model.get("packages") or model.get("components") or []
    for package in packages:
        for model_class in package.get("classes", []):
            name = model_class.get("name", "")
            record = choose_class(index.get(name, []), model_class)
            if record is None:
                kind = "ambiguous" if name in index else "missing"
                model_class["live"] = {"status": kind}
                counts[kind] += 1
                continue

            counts["matched"] += 1
            model_class["live"] = {"status": "synced", "source": str(record["path"])}
            if record["fields"]:
                model_class["fields"] = record["fields"]

            methods = record["methods"]
            ops = model_class.setdefault("ops", [])
            known = {op.get("name") for op in ops}
            for op in ops:
                signature = methods.get(op.get("name"))
                if signature is None:
                    op["live"] = {"status": "missing"}
                    counts["ops_missing"] += 1
                    continue
                op["args"] = signature["args"]
                if "returns" in signature:
                    op["returns"] = signature["returns"]
                else:
                    op.pop("returns", None)
                if signature.get("code"):
                    op["code"] = signature["code"]
                op["live"] = {"status": "synced"}
                counts["ops_updated"] += 1
                if attach_metrics(op, metrics_for(name, signature, rows_by_name)):
                    counts["ops_measured"] += 1
            for method_name, signature in methods.items():
                if method_name in known:
                    continue
                op = {
                    "name": method_name,
                    "args": signature["args"],
                    "live": {"status": "new"},
                }
                if "returns" in signature:
                    op["returns"] = signature["returns"]
                if signature.get("code"):
                    op["code"] = signature["code"]
                attach_metrics(op, metrics_for(name, signature, rows_by_name))
                ops.append(op)
                counts["ops_new"] += 1
    return counts


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="umlview-sync",
        description="Overlay real implementation signatures and CRAP onto a design model.",
    )
    parser.add_argument("model", help="the accepted design model.json")
    parser.add_argument("--source", required=True, help="Python source root to scan")
    parser.add_argument("--crap", help="a crapper text report to read metrics from")
    parser.add_argument("--out", help="output path (default: <model>.live.json)")
    args = parser.parse_args(argv)

    model_path = Path(args.model)
    if not model_path.exists():
        print(f"sync: no such model: {model_path}", file=sys.stderr)
        return 2
    source_root = Path(args.source)
    if not source_root.is_dir():
        print(f"sync: not a directory: {source_root}", file=sys.stderr)
        return 2

    raw = json.loads(model_path.read_text())
    model = json.loads(json.dumps(raw))  # deep copy; the accepted model is not touched
    rows = []
    if args.crap:
        report = Path(args.crap)
        if not report.exists():
            print(f"sync: no such crap report: {report}", file=sys.stderr)
            return 2
        rows = parse_crap(report)
    rows_by_name: dict = {}
    for row in rows:
        rows_by_name.setdefault(row["name"], []).append(row)

    counts = overlay(model, scan_source(source_root), rows_by_name)
    model["live"] = {
        "source_root": str(source_root),
        "crap": str(args.crap) if args.crap else None,
        "counts": counts,
    }
    out_path = (
        Path(args.out)
        if args.out
        else model_path.with_name(model_path.stem + ".live.json")
    )
    out_path.write_text(json.dumps(model, indent=2) + "\n")
    print(
        f"wrote {out_path}  ({counts['matched']} matched, {counts['missing']} missing, "
        f"{counts['ambiguous']} ambiguous; {counts['ops_new']} new ops, "
        f"{counts['ops_measured']} measured)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
