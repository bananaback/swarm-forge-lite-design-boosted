"""Command line for the generated diagram.

Every command is one surgical operation. An agent never has to read the model
or the HTML to change the diagram.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import metrics as metrics_module
import init as init_module
import ir as ir_module
import packaged as packaged_module
import policy as policy_module
import render as render_module
import scan as scan_module
from model import Document, Model, grade, validate_model
from policy import Policy


def _project(config: dict) -> dict:
    """Select the project exactly as tools/design/paths.py does."""
    env = config.get("selector_env", "PACK_PROJECT")
    projects = config.get("projects", {})
    known = ", ".join(sorted(projects)) or "<none configured>"
    name = os.environ.get(env, "").strip() or config.get("default_project")
    if name not in projects:
        raise SystemExit(f"unknown project {name!r} for this pack; known: {known}")
    return projects[name]


def _resolve(args) -> tuple[Path, Path, Path, Policy | None]:
    config_path = Path(args.config).expanduser().resolve()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    pack = config_path.parent.parent
    project_conf = _project(config)
    project = (pack / project_conf["project_root"]).resolve()
    uml = project_conf.get("umlview", {})
    policy_path = (project / uml.get("policy", "umlview.json")).resolve()
    out_dir = (
        project / uml.get("out", project_conf.get("artifacts_root", "tmp") + "/uml")
    ).resolve()
    policy = policy_module.Policy.read(policy_path) if policy_path.is_file() else None
    return project, out_dir, policy_path, policy


def _levels_for(policy: Policy | None, name: str) -> list[list[str]]:
    if not name:
        return policy.levels if policy is not None else []
    if policy is not None:
        for proposal in policy.proposals:
            if proposal.get("name") == name:
                return [
                    list(layer.get("nses", []))
                    for layer in proposal.get("layers", [])
                ]
    raise SystemExit(f"umlview: no proposal {name!r} in the policy")


def _model_path(out_dir: Path) -> Path:
    return out_dir / "model.json"


def _load_document(out_dir: Path) -> Document:
    path = _model_path(out_dir)
    if not path.is_file():
        raise SystemExit(f"umlview: no model at {path}; run `scan` first")
    return Document.read(path)


def _load_model(out_dir: Path) -> Model:
    document = _load_document(out_dir)
    if not document.diagrams:
        raise SystemExit("umlview: the document holds no diagrams")
    return document.diagrams[0]


def _write_policy(args) -> Policy:
    """Derive and write a policy from the code. Never called over an existing one."""
    project, _, policy_path, _ = _resolve(args)
    config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    root_rel = getattr(args, "root", "") or _project(config).get("source_roots", ["."])[0]
    root = (project / root_rel).resolve()
    title = getattr(args, "title", "") or root.name
    probe = Policy(title=title, root=root_rel, prefix=getattr(args, "prefix", "") or "")
    model = scan_module.scan(root, probe)
    prefix = getattr(args, "prefix", "") or init_module.derive_prefix(
        [node.ns for node in model.nodes]
    )
    if prefix != probe.prefix:
        probe.prefix = prefix
        model = scan_module.scan(root, probe)
    levels = init_module.derive_levels(model.nodes, model.edges)
    segments = sorted({node.id.split(".")[0] for node in model.nodes})
    order = [name for level in levels for name in level]
    order += sorted(set(segments) - set(order))
    policy = Policy(
        title=title,
        root=root_rel,
        prefix=prefix,
        order=order,
        levels=levels,
        foreign=model.foreign,
    )
    policy.write(policy_path)
    print(
        f"policy {policy_path.name}: prefix {prefix or '(none)'}  "
        f"segments {len(segments)}  levels {len(levels)}  foreign {len(model.foreign)}"
    )
    for at, level in enumerate(levels):
        print(f"  level {at}: {' '.join(level)}")
    return policy


def cmd_init(args) -> int:
    """Write the first policy from the code, the way the companion agent does."""
    _write_policy(args)
    return 0


def cmd_scan(args) -> int:
    project, out_dir, _, policy = _resolve(args)
    if policy is None:
        policy = _write_policy(args)
    root = (project / policy.root).resolve()
    model = scan_module.scan(root, policy)
    policy_module.apply_edge_kinds(model.edges, policy.edge_kinds)
    violations = policy_module.validate(model.nodes, model.edges, policy.levels)
    matched = metrics_module.attach(model, project / args.metrics, root.name)
    artifacts = (project / args.metrics).parent
    metrics_module.attach_mutation(model, artifacts / "mutate", root.name)
    if policy.is_hierarchical:
        document = Document(title=model.title, diagrams=[model])
    else:
        document = packaged_module.build(policy, model)
    errors = [error for diagram in document.diagrams for error in validate_model(diagram)]
    if errors:
        for error in errors:
            print(f"INVALID {error}")
        return 1
    document.to_path(_model_path(out_dir))
    print(
        f"diagrams {len(document.diagrams)}  nodes {len(model.nodes)}  "
        f"edges {len(model.edges)}  violations {len(violations)}  graded ops {matched}"
    )
    for edge in violations:
        print(f"VIOLATION {edge.src} -> {edge.dst}")
    return 0


def cmd_validate(args) -> int:
    _, out_dir, _, policy = _resolve(args)
    model = _load_model(out_dir)
    levels = _levels_for(policy, getattr(args, "proposal", "")) or model.levels
    violations = policy_module.validate(model.nodes, model.edges, levels)
    for edge in violations:
        print(f"VIOLATION {edge.src} -> {edge.dst}")
    if not violations:
        print(f"ok  nodes {len(model.nodes)}  edges {len(model.edges)}")
    return 1 if violations else 0


def cmd_load(args) -> int:
    """Read a hand-authored EDN or JSON IR into model.json."""
    _, out_dir, _, _ = _resolve(args)
    document = ir_module.load_document(Path(args.path).expanduser().resolve())
    errors = [error for diagram in document.diagrams for error in validate_model(diagram)]
    if errors:
        for error in errors:
            print(f"INVALID {error}")
        return 1
    document.to_path(_model_path(out_dir))
    first = document.diagrams[0]
    print(
        f"loaded {args.path}: diagrams {len(document.diagrams)}  mode {first.mode}  "
        f"packages {len(first.packages)}  "
        f"classes {sum(len(package.classes) for package in first.packages)}  "
        f"edges {len(first.edges)}"
    )
    return 0


def cmd_render(args) -> int:
    _, out_dir, _, policy = _resolve(args)
    document = _load_document(out_dir)
    proposals = policy.proposals if policy is not None else []
    target = render_module.render(document, out_dir / "viewer.html", proposals)
    print(f"wrote {target}  ({target.stat().st_size // 1024} KiB)")
    return 0


def _children(model: Model, prefix: str) -> dict[str, list[str]]:
    children: dict[str, list[str]] = {}
    for node in model.nodes:
        if prefix and not node.id.startswith(prefix + "."):
            continue
        rest = node.id[len(prefix) + 1 :] if prefix else node.id
        head = rest.split(".", 1)[0]
        children.setdefault(head, []).append(node.id)
    return children


def _order_key(model: Model, name: str):
    position = model.order.index(name) if name in model.order else len(model.order)
    return position, name


def cmd_ls(args) -> int:
    _, out_dir, _, _ = _resolve(args)
    model = _load_model(out_dir)
    if args.violations:
        _, _, _, policy = _resolve(args)
        levels = _levels_for(policy, getattr(args, "proposal", "")) or model.levels
        violations = policy_module.validate(model.nodes, model.edges, levels)
        for edge in violations:
            print(f"{edge.src} -> {edge.dst}")
        return 1 if violations else 0
    children = _children(model, args.at or "")
    for name in sorted(children, key=lambda value: _order_key(model, value)):
        ids = children[name]
        full = f"{args.at}.{name}" if args.at else name
        leaf = ids == [full]
        count = len(ids)
        suffix = "" if leaf else f"/  ({count} module{'s' if count != 1 else ''})"
        print(f"{name}{suffix}")
    return 0


def cmd_show(args) -> int:
    _, out_dir, _, _ = _resolve(args)
    model = _load_model(out_dir)
    node = model.index().get(args.id)
    if node is None:
        raise SystemExit(f"umlview: no module {args.id}")
    print(f"{node.id}  ns {node.ns}")
    print(
        f"cc {node.cc}  coverage {node.coverage}  crap {node.crap}  grade {grade(node.crap)}"
    )
    for op in node.ops:
        print(f"  {op.name}  cc {op.cc}  cov {op.coverage}  crap {op.crap}")
    return 0


def cmd_policy(args) -> int:
    _, _, policy_path, policy = _resolve(args)
    if policy is None:
        raise SystemExit("umlview: no policy file; write one at the configured path")
    action = args.action
    if action == "order":
        policy.order = list(args.values)
    elif action == "level":
        while len(policy.levels) < args.rank:
            policy.levels.append([])
        level = policy.levels[args.rank - 1]
        for value in args.values:
            if value not in level:
                level.append(value)
    elif action == "foreign":
        for value in args.values:
            if value not in policy.foreign:
                policy.foreign.append(value)
    elif action == "omit":
        for value in args.values:
            if value not in policy.omit:
                policy.omit.append(value)
    elif action == "propose":
        if len(args.values) < 2:
            raise SystemExit("usage: policy propose NAME 'Label=a,b' ['Label=c'...]")
        name = args.values[0]
        layers = []
        for spec in args.values[1:]:
            label, _, members = spec.partition("=")
            if not members:
                label, members = label, label
            layers.append(
                {
                    "id": label.strip().lower().replace(" ", "-") or f"layer-{len(layers)}",
                    "label": label.strip(),
                    "nses": [value for value in members.split(",") if value],
                }
            )
        policy.proposals = [p for p in policy.proposals if p.get("name") != name]
        policy.proposals.append({"name": name, "layers": layers, "omit": []})
    elif action == "edge-kind":
        if len(args.values) != 3:
            raise SystemExit("usage: policy edge-kind FROM TO KIND")
        policy.edge_kinds[f"{args.values[0]}->{args.values[1]}"] = args.values[2]
    else:
        print(json.dumps(policy.__dict__, indent=2))
        return 0
    policy.write(policy_path)
    print(f"policy {action}: {' '.join(args.values)}")
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="umlview", description=__doc__)
    parser.add_argument(
        "--config",
        default=str(Path(__file__).resolve().parents[2] / "config" / "pack.json"),
    )
    parser.add_argument("--metrics", default="", help="crap.edn relative to the project root")
    commands = parser.add_subparsers(dest="command", required=True)

    initial = commands.add_parser("init", help="write the first policy from the code")
    initial.add_argument("--root", default="", help="source tree, relative to the project")
    initial.add_argument("--prefix", default="", help="namespace prefix to strip")
    initial.add_argument("--title", default="")
    loading = commands.add_parser("load", help="authored IR (EDN or JSON) -> model.json")
    loading.add_argument("path")
    commands.add_parser("scan", help="source + policy -> model.json")
    validating = commands.add_parser(
        "validate", help="dependency rule only; exit 1 on a violation"
    )
    validating.add_argument("--proposal", default="")
    commands.add_parser("render", help="model.json -> viewer.html")
    listing = commands.add_parser("ls", help="list children at a level")
    listing.add_argument("--at", default="")
    listing.add_argument("--violations", action="store_true")
    listing.add_argument("--proposal", default="")
    show = commands.add_parser("show", help="one module and its functions")
    show.add_argument("id")
    policy_parser = commands.add_parser("policy", help="edit the policy")
    policy_parser.add_argument(
        "action",
        choices=["show", "order", "level", "foreign", "omit", "edge-kind", "propose"],
    )
    policy_parser.add_argument("values", nargs="*")
    policy_parser.add_argument("--rank", type=int, default=0)

    args = parser.parse_args(argv)
    if not args.metrics:
        config = json.loads(Path(args.config).read_text(encoding="utf-8"))
        artifacts = _project(config).get("artifacts_root", "tmp")
        args.metrics = str(artifacts).rstrip("/") + "/.metrics/crap.edn"
    return {
        "init": cmd_init,
        "load": cmd_load,
        "scan": cmd_scan,
        "validate": cmd_validate,
        "render": cmd_render,
        "ls": cmd_ls,
        "show": cmd_show,
        "policy": cmd_policy,
    }[args.command](args)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
