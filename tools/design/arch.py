#!/usr/bin/env python3
"""One design surface for agents: query, validate and render the two views.

There is no stored model. Every command scans the code and merges the authored
runtime model, so a query can never disagree with the source:

    arch classes ls|show|deps [--transitive]|validate|render
    arch runtime ls|show|validate|render
    arch render [classes|runtime|all]
    arch env

The project is chosen by the `PACK_PROJECT` environment variable, or by the
config's `default_project` when it is unset; `arch env` prints the resolution.

`umlview` stays the module-grade view and is not touched here.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import paths  # noqa: E402
import overlay  # noqa: E402
import class_model as class_map  # noqa: E402
import runtime_view  # noqa: E402

if paths.SUBSYSTEMS:
    class_map.DIAGRAMS = paths.SUBSYSTEMS

PIPELINE = paths.PIPELINE
DOCS = paths.DOCS
RUNTIME = paths.RUNTIME
SPEC_DIR = paths.DOCS / "specs"

SPECS = paths.SPECS
SECTIONS = ("Responsibility", "Structure", "Classes", "Flow", "Design rules", "Rejected")


def _overlay() -> dict:
    return overlay.load(paths.DESIGN)


def _code_classes() -> dict[str, class_map.ClassInfo]:
    return {cid: info for cid, (_sub, info) in class_map.all_classes(PIPELINE, None).items()}


def _code_edges() -> list[tuple[str, str, str]]:
    edges: list[tuple[str, str, str]] = []
    for _label, (_number, _classes, sub_edges) in class_map.merged(PIPELINE, None).items():
        edges.extend(sub_edges)
    return edges


def _labelled() -> dict[str, tuple[str, class_map.ClassInfo]]:
    return class_map.all_classes(PIPELINE, _overlay())


def _classes(labelled: dict[str, tuple[str, class_map.ClassInfo]]) -> dict[str, class_map.ClassInfo]:
    return {cid: info for cid, (_sub, info) in labelled.items()}


def _edge_map() -> dict[str, list]:
    return {label: edges for label, (_n, _c, edges) in class_map.merged(PIPELINE, _overlay()).items()}


def _cid(info: class_map.ClassInfo) -> str:
    return class_map.class_id(info)


def _lookup(classes, key: str):
    if key in classes:
        return classes[key]
    matches = [info for info in classes.values() if info.name == key]
    return matches[0] if len(matches) == 1 else None


def _edges(_classes):
    edges = []
    for sub_edges in _edge_map().values():
        edges.extend(sub_edges)
    return edges


def _require_tree() -> bool:
    """An absent tree, or one with no declared subsystems, must never look
    like a clean, empty project."""
    if not class_map.DIAGRAMS:
        print(
            f"no subsystems declared for project {paths.NAME!r} in config/pack.json"
        )
        return False
    if PIPELINE.is_dir():
        return True
    print(f"no class tree for project {paths.NAME!r}: {PIPELINE}")
    return False


def cmd_classes_ls(args) -> int:
    if not _require_tree():
        return 1
    for cid, (subsystem, info) in sorted(_labelled().items()):
        if args.subsystem and subsystem != args.subsystem:
            continue
        if args.kind and info.stereotype != args.kind:
            continue
        if args.layer and info.layer != args.layer:
            continue
        if args.group and info.group != args.group:
            continue
        members = len(info.methods)
        print(f"{cid:58} {info.stereotype:10} {info.layer:5} {members} members  {info.module}.py")
    return 0


def cmd_classes_show(args) -> int:
    labelled = _labelled()
    classes = _classes(labelled)
    info = _lookup(classes, args.id)
    if info is None:
        matches = [cid for cid, inf in classes.items() if inf.name == args.id]
        if matches:
            print(f"arch: {args.id!r} is ambiguous; use one of:", file=sys.stderr)
            for cid in sorted(matches):
                print(f"  {cid}", file=sys.stderr)
        else:
            print(f"arch: no class {args.id!r}", file=sys.stderr)
        return 1
    print(f"{info.name}  {class_map.STEREOTYPES[info.stereotype][0] or '«class»'}  {info.layer}  {info.module}.py")
    print("  methods: " + (", ".join(info.methods) or "—"))
    for src, dst, kind in _edges(classes):
        if src == info.name:
            print(f"  out: {dst} ({kind})")
        elif dst == info.name:
            print(f"  in:  {src} ({kind})")
    return 0


def cmd_classes_deps(args) -> int:
    labelled = _labelled()
    classes = _classes(labelled)
    info = _lookup(classes, args.id)
    if info is None:
        matches = [cid for cid, inf in classes.items() if inf.name == args.id]
        if matches:
            print(f"arch: {args.id!r} is ambiguous; use one of:", file=sys.stderr)
            for cid in sorted(matches):
                print(f"  {cid}", file=sys.stderr)
        else:
            print(f"arch: no class {args.id!r}", file=sys.stderr)
        return 1
    cid = _cid(info)
    subsystem = labelled[cid][0]
    edges = _edge_map().get(subsystem, [])
    seen = {info.name}
    frontier = [info.name]
    rows = []
    while frontier:
        current = frontier.pop(0)
        for src, dst, kind in edges:
            if dst == current and src not in seen:
                seen.add(src)
                rows.append((src, kind, current))
                frontier.append(src)
        if not args.transitive:
            break
    for dependent, kind, via in rows:
        print(f"{dependent:44} {kind:12} via {via}")
    if not rows:
        print("(no dependents)")
    return 0


def cmd_classes_validate(_args) -> int:
    if not _require_tree():
        return 1
    problems = []
    total_classes = total_edges = 0
    for _label, (_number, classes, edges) in class_map.merged(PIPELINE, _overlay()).items():
        total_classes += len(classes)
        total_edges += len(edges)
        for src, dst, edge_kind in edges:
            if src not in classes or dst not in classes:
                problems.append(f"dangling edge {src} -> {dst}")
                continue
            explicit = lambda info: {"core", "shell"} & set(info.module.split("/"))
            if (edge_kind != "dependency" and explicit(classes[src]) and explicit(classes[dst])
                    and classes[src].layer == "core" and classes[dst].layer == "shell"):
                problems.append(f"core depends on shell: {src} -> {dst} ({edge_kind})")
        outgoing: dict[str, list[str]] = {}
        for src, dst, kind in edges:
            if kind != "dependency":
                outgoing.setdefault(src, []).append(dst)
        state: dict[str, int] = {}

        def visit(node, trail):
            if state.get(node) == 1:
                problems.append("cycle: " + " -> ".join(trail + [node]))
                return
            if state.get(node) == 2:
                return
            state[node] = 1
            for nxt in outgoing.get(node, []):
                visit(nxt, trail + [node])
            state[node] = 2

        for name in outgoing:
            visit(name, [])
    data = _overlay()
    code_ids = set(_code_classes())
    code_edges = set(_code_edges())
    for problem in overlay.validate(data, code_ids, code_edges):
        problems.append("overlay: " + problem)
    if problems:
        for problem in sorted(set(problems)):
            print("violation:", problem)
        return 1
    print(f"ok: {total_classes} classes, {total_edges} edges, 0 violations")
    return 0


def cmd_classes_render(_args) -> int:
    if not _require_tree():
        return 1
    class_map.render(
        PIPELINE, DOCS / "diagrams.html", _overlay(), project=paths.NAME
    )
    return 0


def cmd_classes_add(args) -> int:
    data = _overlay()
    if args.what == "node":
        if args.subsystem not in {entry[1] for entry in class_map.DIAGRAMS}:
            print(f"arch: unknown subsystem {args.subsystem!r}", file=sys.stderr)
            return 1
        node = {
            "id": args.id, "subsystem": args.subsystem,
            "stereotype": args.stereotype, "layer": args.layer,
            "module": args.module or args.id.rsplit(".", 1)[0].replace(".", "/"),
            "note": args.note or "", "reason": args.reason or "",
            "since": overlay.today(),
        }
        overlay.add_node(data, node)
    else:
        overlay.add_edge(data, {
            "from": args.source, "to": args.target, "kind": args.kind,
            "reason": args.reason or "", "since": overlay.today(),
        })
    overlay.save(paths.DESIGN, data)
    print(f"design: {args.what} recorded in {paths.DESIGN}")
    return 0


def cmd_classes_remove(args) -> int:
    data = _overlay()
    if args.what == "node":
        ok = overlay.remove_node(data, args.id)
    else:
        ok = overlay.remove_edge(data, args.source, args.target)
    if not ok:
        print("arch: nothing removed (the overlay holds no such entry)", file=sys.stderr)
        return 1
    overlay.save(paths.DESIGN, data)
    print(f"design: {args.what} removed")
    return 0


def cmd_classes_annotate(args) -> int:
    data = _overlay()
    overlay.annotate(data, args.id, args.note, args.layer)
    overlay.save(paths.DESIGN, data)
    print(f"design: annotation recorded for {args.id}")
    return 0


def cmd_classes_diff(args) -> int:
    data = _overlay()
    rows = overlay.diff(set(_code_classes()), set(_code_edges()), data)
    for row in rows:
        print(row)
    if not rows:
        print("(overlay empty)")
    stale = any(row.startswith("stale") for row in rows)
    if args.strict and stale:
        return 1
    return 0


def docs_problems(spec_dir: Path, labelled: dict[str, tuple[str, object]]) -> list[str]:
    import re

    problems = []
    covered: dict[str, set[str]] = {}
    for filename, subsystem in SPECS.items():
        path = spec_dir / filename
        if not path.is_file():
            problems.append(f"{filename}: missing")
            continue
        text = path.read_text(encoding="utf-8")
        heads = re.findall(r"^## (.+)$", text, re.M)
        missing = [section for section in SECTIONS if section not in heads]
        if missing:
            problems.append(f"{filename}: missing sections {', '.join(missing)}")
        body = re.sub(r"^Behavior:.*$", "", text, flags=re.M)
        if re.search(r"tests/|\btest_[a-z]|\bAC\d|\bR\d+\b", body):
            problems.append(f"{filename}: mentions tests, acceptance or requirement ids")
        covered.setdefault(subsystem, (set(), text))[0].update(
            re.findall(r"`([A-Z][A-Za-z0-9]+)`", text)
        )
    for subsystem, (names, text) in covered.items():
        expected = {info.name for cid, (sub, info) in labelled.items()
                    if sub == subsystem and not info.name.startswith("_")}
        absent = sorted(name for name in expected if name not in text)
        if absent:
            problems.append(f"{subsystem}: classes not described: {', '.join(absent)}")
    return problems


def cmd_docs_validate(_args) -> int:
    if not _require_tree():
        return 1
    if not SPECS:
        print(f"no specs declared for project {paths.NAME!r} in config/pack.json")
        return 1
    if not SPEC_DIR.is_dir():
        print(f"no specs directory: {SPEC_DIR}")
        return 1
    problems = docs_problems(SPEC_DIR, class_map.all_classes(PIPELINE, _overlay()))
    if problems:
        for problem in problems:
            print("violation:", problem)
        return 1
    print(f"ok: {len(SPECS)} specs, every class described, no test references")
    return 0


def _runtime():
    if not RUNTIME.is_file():
        raise SystemExit(f"no runtime model for project {paths.NAME!r}: {RUNTIME}")
    return json.loads(RUNTIME.read_text(encoding="utf-8"))


def cmd_runtime_ls(_args) -> int:
    data = _runtime()
    for node in data["nodes"]:
        print(f"{node['id']:18} {node['tone']:9} {node['label']:24} {node.get('sub', '')}")
    return 0


def cmd_runtime_show(args) -> int:
    data = _runtime()
    node = next((n for n in data["nodes"] if n["id"] == args.id), None)
    if node is None:
        print(f"arch: no runtime node {args.id!r}", file=sys.stderr)
        return 1
    print(f"{node['label']}  {node['tone']}  {node.get('sub', '')}")
    for edge in data["edges"]:
        if edge["from"] == args.id:
            print(f"  out: {edge['to']} ({edge['kind']})")
        if edge["to"] == args.id:
            print(f"  in:  {edge['from']} ({edge['kind']})")
    return 0


def runtime_problems(data: dict, pipeline: Path) -> list[str]:
    ids = [n["id"] for n in data["nodes"]]
    problems = []
    if len(ids) != len(set(ids)):
        problems.append("duplicate runtime node id")
    known = set(ids) | {z.get("id") for z in data.get("zones", [])}
    for edge in data["edges"]:
        if edge["from"] not in known:
            problems.append(f"edge from unknown node {edge['from']}")
        if edge["to"] not in known:
            problems.append(f"edge to unknown node {edge['to']}")
    packages = {p.name for p in pipeline.iterdir() if p.is_dir() and not p.name.startswith("__")}
    boxed = {n["package"] for n in data["nodes"] if n.get("package")}
    missing = sorted(packages - boxed)
    if missing:
        problems.append("code subsystems with no box: " + ", ".join(missing))
    return problems


def cmd_runtime_validate(_args) -> int:
    data = _runtime()
    ids = [n["id"] for n in data["nodes"]]
    problems = runtime_problems(data, PIPELINE)
    if problems:
        for problem in problems:
            print("violation:", problem)
        return 1
    print(f"ok: {len(ids)} boxes, {len(data['edges'])} edges, every code subsystem boxed")
    return 0


def cmd_runtime_render(_args) -> int:
    runtime_view.render(RUNTIME, DOCS / "ARCHITECTURE.html")
    return 0


def cmd_render(args) -> int:
    if args.view in ("classes", "all"):
        cmd_classes_render(None)
    if args.view in ("runtime", "all"):
        cmd_runtime_render(None)
    return 0


def cmd_env(_args) -> int:
    """Print the resolved project, so a report can prove which one it ran against."""
    runtime = "present" if RUNTIME.is_file() else "missing"
    origin = paths.SOURCE
    if origin == "default_project":
        origin = f"default_project ({paths.SELECTOR_ENV} unset)"
    print(f"project:      {paths.NAME}")
    print(f"selected by:  {origin}")
    print(f"project_root: {paths.PROJECT}")
    print(f"app:          {paths.APP}")
    print(f"class_root:   {paths.PIPELINE}")
    print(f"docs:         {paths.DOCS}")
    print(f"architecture: {paths.ARCHITECTURE}")
    print(f"runtime:      {paths.RUNTIME} ({runtime})")
    print(f"tmp:          {paths.ARTIFACTS}")
    print(f"specs:        {len(SPECS)} declared")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="arch", description=__doc__)
    sub = parser.add_subparsers(dest="domain", required=True)

    classes = sub.add_parser("classes", help="class design view")
    csub = classes.add_subparsers(dest="action", required=True)
    ls = csub.add_parser("ls")
    ls.add_argument("--kind", choices=sorted(class_map.STEREOTYPES))
    ls.add_argument("--layer", choices=("core", "shell"))
    ls.add_argument("--group")
    ls.add_argument("--subsystem")
    ls.set_defaults(func=cmd_classes_ls)
    show = csub.add_parser("show")
    show.add_argument("id")
    show.set_defaults(func=cmd_classes_show)
    deps = csub.add_parser("deps")
    deps.add_argument("id")
    deps.add_argument("--transitive", action="store_true")
    deps.set_defaults(func=cmd_classes_deps)
    csub.add_parser("validate").set_defaults(func=cmd_classes_validate)
    csub.add_parser("render").set_defaults(func=cmd_classes_render)
    add = csub.add_parser("add")
    add.add_argument("what", choices=("node", "edge"))
    add.add_argument("id", nargs="?")
    add.add_argument("source", nargs="?")
    add.add_argument("target", nargs="?")
    add.add_argument("--subsystem")
    add.add_argument("--stereotype", default="class", choices=sorted(set(class_map.STEREOTYPES) | {"class"}))
    add.add_argument("--layer", default="core", choices=("core", "shell"))
    add.add_argument("--module")
    add.add_argument("--kind", default="dependency", choices=overlay.VALID_KINDS)
    add.add_argument("--note")
    add.add_argument("--reason")
    add.set_defaults(func=cmd_classes_add)
    remove = csub.add_parser("remove")
    remove.add_argument("what", choices=("node", "edge"))
    remove.add_argument("id", nargs="?")
    remove.add_argument("source", nargs="?")
    remove.add_argument("target", nargs="?")
    remove.set_defaults(func=cmd_classes_remove)
    annotate = csub.add_parser("annotate")
    annotate.add_argument("id")
    annotate.add_argument("--note")
    annotate.add_argument("--layer", choices=("core", "shell"))
    annotate.set_defaults(func=cmd_classes_annotate)
    diff = csub.add_parser("diff")
    diff.add_argument("--strict", action="store_true")
    diff.set_defaults(func=cmd_classes_diff)

    runtime = sub.add_parser("runtime", help="runtime architecture view")
    rsub = runtime.add_subparsers(dest="action", required=True)
    rsub.add_parser("ls").set_defaults(func=cmd_runtime_ls)
    rshow = rsub.add_parser("show")
    rshow.add_argument("id")
    rshow.set_defaults(func=cmd_runtime_show)
    rsub.add_parser("validate").set_defaults(func=cmd_runtime_validate)
    rsub.add_parser("render").set_defaults(func=cmd_runtime_render)

    docs = sub.add_parser("docs", help="specs vs the class model")
    dsub = docs.add_subparsers(dest="action", required=True)
    dsub.add_parser("validate").set_defaults(func=cmd_docs_validate)

    sub.add_parser("env", help="resolved project and its paths").set_defaults(func=cmd_env)

    render = sub.add_parser("render")
    render.add_argument("view", nargs="?", default="all", choices=("classes", "runtime", "all"))
    render.set_defaults(func=cmd_render)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
