"""Scan Python source into the generated model.

One node per module; functions and methods become ops; project imports become
dependency edges; anything else becomes a foreign library.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

from model import KIND_DEPENDENCY, KIND_RANK, Edge, Model, Node, Op
from policy import Policy, omitted

SKIP_PARTS = {"__pycache__", ".git", ".venv", "node_modules", "build", "dist"}


@dataclass
class _Module:
    name: str
    path: Path
    package: str
    imports: list[str]
    foreign: set[str]
    ops: list[Op]


def _module_name(package: str, relative: Path) -> str:
    parts = list(relative.parts)
    parts[-1] = parts[-1][:-3]
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join([package, *parts]) if parts else package


def _resolve_relative(current_package: str, level: int, module: str | None) -> str:
    parts = current_package.split(".")
    keep = len(parts) - (level - 1)
    base = ".".join(parts[: max(keep, 0)])
    if module:
        return f"{base}.{module}" if base else module
    return base


def _ops(tree: ast.Module) -> list[Op]:
    ops: list[Op] = []

    def walk(body, prefix: str) -> None:
        for statement in body:
            if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef)):
                ops.append(Op(name=f"{prefix}{statement.name}"))
            elif isinstance(statement, ast.ClassDef):
                walk(statement.body, f"{prefix}{statement.name}.")

    walk(tree.body, "")
    return ops


def _imports(
    tree: ast.Module, package: str, known: dict[str, str], root_package: str
) -> tuple[list[str], set[str]]:
    targets: list[str] = []
    foreign: set[str] = set()

    def admit(candidate: str) -> None:
        if candidate in known:
            targets.append(candidate)
            return
        parent = candidate.rsplit(".", 1)[0]
        if parent in known:
            targets.append(parent)
            return
        internal = candidate == root_package or candidate.startswith(root_package + ".")
        if not internal:
            foreign.add(candidate.split(".", 1)[0])

    for statement in ast.walk(tree):
        if isinstance(statement, ast.Import):
            for alias in statement.names:
                admit(alias.name)
        elif isinstance(statement, ast.ImportFrom):
            module = statement.module or ""
            if statement.level:
                base = _resolve_relative(package, statement.level, module)
            else:
                base = module
            if not base:
                continue
            admit(base)
            for alias in statement.names:
                admit(f"{base}.{alias.name}")
    return targets, foreign


def _module_of(path: Path, root: Path) -> Path:
    return path.relative_to(root)


def _collapse(names: set[str], prefixes: list[str]) -> list[str]:
    """Keep the longest listed foreign prefix under each import, as collapse-id does."""
    if not prefixes:
        return sorted(names)
    collapsed: set[str] = set()
    for name in names:
        matches = [
            prefix
            for prefix in prefixes
            if name == prefix or name.startswith(prefix + ".")
        ]
        if matches:
            collapsed.add(max(matches, key=len))
    return sorted(collapsed)


def _merge_edges(edges: list[Edge]) -> list[Edge]:
    """Keep the strongest kind per endpoint pair; a bundled violation survives."""
    merged: dict[tuple[str, str], Edge] = {}
    for edge in edges:
        key = (edge.src, edge.dst)
        kept = merged.get(key)
        if kept is None or KIND_RANK.get(edge.kind, 0) > KIND_RANK.get(kept.kind, 0):
            merged[key] = Edge(src=edge.src, dst=edge.dst, kind=edge.kind)
    result = [merged[key] for key in sorted(merged)]
    for edge in result:
        edge.violating = edge.kind == KIND_DEPENDENCY
    return result


def scan(root: Path, policy: Policy) -> Model:
    """Read every module under the policy root and build the model."""
    package = root.name
    files = sorted(
        path
        for path in root.rglob("*.py")
        if not SKIP_PARTS & set(path.parts) and path.name != "__init__.py"
    )
    if not files:
        raise FileNotFoundError(f"no Python modules under {root}")

    known = {_module_name(package, _module_of(path, root)): str(path) for path in files}

    modules: list[_Module] = []
    for path in files:
        name = _module_name(package, _module_of(path, root))
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        package_name = name.rsplit(".", 1)[0] if "." in name else name
        targets, foreign = _imports(tree, package_name, known, package)
        modules.append(
            _Module(
                name=name,
                path=path,
                package=package_name,
                imports=targets,
                foreign=foreign,
                ops=_ops(tree),
            )
        )

    def strip(name: str) -> str:
        if policy.prefix and name.startswith(policy.prefix + "."):
            return name[len(policy.prefix) + 1 :]
        return name

    kept = [module for module in modules if not omitted(strip(module.name), policy.omit)]
    ids = {module.name: strip(module.name) for module in kept}

    nodes = [
        Node(id=ids[module.name], ns=module.name, name=ids[module.name].rsplit(".", 1)[-1], ops=module.ops)
        for module in kept
        if ids[module.name]
    ]
    edges: list[Edge] = []
    seen: set[tuple[str, str]] = set()
    foreign: set[str] = set()
    foreign_links: list[tuple[str, str]] = []
    for module in kept:
        source = ids.get(module.name)
        if not source:
            continue
        for target in module.imports:
            destination = ids.get(target)
            if not destination or destination == source:
                continue
            pair = (source, destination)
            if pair in seen:
                continue
            seen.add(pair)
            edges.append(Edge(src=source, dst=destination))
        for name in module.foreign:
            matches = [
                prefix
                for prefix in policy.foreign
                if name == prefix or name.startswith(prefix + ".")
            ]
            if matches:
                foreign_links.append((source, max(matches, key=len)))
        foreign |= module.foreign

    collapsed = _collapse(foreign, policy.foreign)
    allowed = set(collapsed)
    for source, target in foreign_links:
        if target in allowed:
            pair = (source, target)
            if pair not in seen:
                seen.add(pair)
                edges.append(Edge(src=source, dst=target))
    foreign_nodes = [
        Node(id=name, ns=name, name=name, foreign=True) for name in collapsed
    ]
    edges = _merge_edges(edges)
    omitted_pairs = {tuple(pair) for pair in policy.omit_edges if len(pair) == 2}
    if omitted_pairs:
        edges = [edge for edge in edges if (edge.src, edge.dst) not in omitted_pairs]
    return Model(
        title=policy.title or package,
        prefix=policy.prefix,
        nodes=nodes,
        edges=edges,
        foreign=collapsed,
        foreign_classes=foreign_nodes,
        order=list(policy.order),
        levels=[list(level) for level in policy.levels],
    )
