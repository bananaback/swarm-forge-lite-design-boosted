#!/usr/bin/env python3
"""umlview scan -- Python source -> model.json, mirroring uml-viewer's graph_clojure.

This is the one part we swap for a different language. It reproduces the Clojure
LanguageGraph's shape: one node per module (his one node per namespace), where

  - a project import                              -> ``:dependency`` edge
  - a class based on a project Protocol/ABC       -> ``:implements`` edge
  - an import outside the project                 -> a ``:foreign`` class + edge
  - a module defining a Protocol/ABC              -> ``:stereotype :interface``

Members (fields/ops) are not authored by upstream's parser; we fill them from the Python
source so the boxes are useful. Secrets, core/shell, and ``levels`` are authored later.

Limits: star imports and computed imports are not resolved. If your package root is
``app``, scan its parent and pass ``--prefix app`` so ids and imports line up.

Usage:
  scan_python.py SRC_ROOT [--prefix P] [--out model.json] [--title TITLE] [--include-private]
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from pathlib import Path

PROTOCOL_BASES = {"Protocol", "ABC", "ABCMeta"}


def as_id(value: str) -> str:
    return re.sub(r"\s+", "-", str(value)).lower()


def camel(segment: str) -> str:
    return "".join(part.capitalize() for part in re.split(r"[-_]", segment) if part)


def raw_module(rel: Path) -> str:
    parts = list(rel.with_suffix("").parts)
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts) if parts else rel.stem


def package_of(raw: str) -> str:
    return raw.rsplit(".", 1)[0] if "." in raw else ""


def resolve_from(current: str, level: int, module: str | None) -> str:
    """Absolute module a ``from`` targets. Level 0 is absolute; level 1 is the current
    package, and each extra level goes up one."""
    if not level:
        return module or ""
    parts = package_of(current).split(".") if package_of(current) else []
    up = max(level - 1, 0)
    base = parts[: len(parts) - up] if up else parts
    if module:
        return ".".join(base + module.split("."))
    return ".".join(base)


def imports_of(tree: ast.AST, current: str) -> dict:
    """{absolute module or package: [names imported from it]} for one module."""
    out: dict = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                out.setdefault(a.name, []).append(a.name.split(".")[-1])
        elif isinstance(node, ast.ImportFrom):
            base = resolve_from(current, node.level, node.module)
            if node.module:
                out.setdefault(base, []).extend(a.name for a in node.names)
            else:  # `from . import submodule` -> targets are submodules
                for a in node.names:
                    out.setdefault((base + "." + a.name).lstrip("."), []).append(a.name)
    return out


def member_op(fn: ast.AST, include_private: bool) -> dict:
    name = fn.name
    if name.startswith("__") and name.endswith("__") and name != "__init__":
        return {}
    if not include_private and name.startswith("_") and not name.startswith("__"):
        return {}
    op = {"name": name, "args": [a.arg for a in fn.args.args if a.arg not in ("self", "cls")],
          "private": name.startswith("_")}
    if getattr(fn, "returns", None) is not None:
        try:
            op["returns"] = ast.unparse(fn.returns)
        except Exception:
            pass
    return op


def scan(root: Path, prefix: str, include_private: bool) -> dict:
    trees = {}
    for path in sorted(p for p in root.rglob("*.py") if "__pycache__" not in p.parts):
        trees[raw_module(path.relative_to(root))] = ast.parse(
            path.read_text(encoding="utf-8", errors="replace"))
    known = set(trees)

    def class_id(raw: str) -> str:
        dot = prefix + "."
        return as_id(raw[len(dot):]) if prefix and raw.startswith(dot) else as_id(raw)

    protocols = {
        raw for raw, tree in trees.items()
        for node in tree.body if isinstance(node, ast.ClassDef)
        for b in node.bases if getattr(b, "id", getattr(b, "attr", "")) in PROTOCOL_BASES
    }

    packages: dict = {}
    edges: list = []
    foreign: dict = {}
    for raw, tree in trees.items():
        cid = class_id(raw)
        node = {"id": cid, "name": camel(raw.split(".")[-1]), "ns": raw,
                "stereotype": "interface" if raw in protocols else "class",
                "fields": [], "ops": []}
        bases = set()
        for stmt in tree.body:
            if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
                op = member_op(stmt, include_private)
                if op:
                    node["ops"].append(op)
            elif isinstance(stmt, ast.ClassDef):
                for b in stmt.bases:
                    name = getattr(b, "id", None) or getattr(b, "attr", None)
                    if name:
                        bases.add(name)
                for inner in stmt.body:
                    if isinstance(inner, ast.AnnAssign) and isinstance(inner.target, ast.Name):
                        typ = ast.unparse(inner.annotation) if inner.annotation else ""
                        node["fields"].append({"text": (f"{inner.target.id} : {typ}").rstrip(" :")})
                    elif isinstance(inner, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        op = member_op(inner, include_private)
                        if op:
                            node["ops"].append(op)

        emitted = set()
        tops = {raw.split(".")[0] for raw in known}
        for target, names in imports_of(tree, raw).items():
            # a name may name a submodule: promote it to its own target when it is scanned
            candidates = {target} | {target + "." + n for n in names if target + "." + n in known}
            for t in candidates:
                if t in known:
                    if t == raw or t in emitted:
                        continue
                    emitted.add(t)
                    edges.append({"from": cid, "to": class_id(t), "kind": "dependency"})
                    if t in protocols and bases & set(names):
                        edges.append({"from": cid, "to": class_id(t), "kind": "implements"})
                elif target.split(".")[0] and target.split(".")[0] not in tops:
                    top = target.split(".")[0]
                    foreign.setdefault(top, {"id": as_id(top), "name": top, "foreign": True})
                    edges.append({"from": cid, "to": as_id(top), "kind": "dependency"})

        top_seg = cid.split(".")[0]
        packages.setdefault(top_seg, {"id": top_seg, "label": top_seg, "classes": []})
        packages[top_seg]["classes"].append(node)

    ids = {c["id"] for p in packages.values() for c in p["classes"]}
    edges = [e for e in edges if e["from"] in ids and (e["to"] in ids or e["to"] in foreign)]
    return {"title": root.name, "packages": list(packages.values()),
            "foreign": list(foreign.values()), "edges": edges}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="umlview-scan")
    parser.add_argument("root")
    parser.add_argument("--prefix", default="")
    parser.add_argument("--out")
    parser.add_argument("--title")
    parser.add_argument("--include-private", action="store_true")
    args = parser.parse_args(argv)
    root = Path(args.root)
    if not root.is_dir():
        print(f"scan: not a directory: {root}", file=sys.stderr)
        return 2
    model = scan(root, args.prefix, args.include_private)
    if args.title:
        model["title"] = args.title
    out = Path(args.out) if args.out else root / "model.json"
    out.write_text(json.dumps(model, indent=2) + "\n")
    classes = sum(len(p["classes"]) for p in model["packages"])
    print(f"wrote {out}  ({len(model['packages'])} packages, {classes} modules, "
          f"{len(model['edges'])} edges, {len(model['foreign'])} foreign)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
