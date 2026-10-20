"""Derive a first policy from the code: prefix, order, levels, foreign.

Uncle bob's companion agent writes and maintains the policy; the operator does
not hand-author it. This does the same, from the observed namespace tree and the
observed dependency direction.
"""

from __future__ import annotations

from collections import Counter, defaultdict

from model import Edge, Node
from policy import Policy, segment


def derive_prefix(names: list[str]) -> str:
    """The deepest prefix that still leaves several top-level segments.

    The namespace tree usually has one dominant root (``app.pipeline``) and a
    few stragglers (``app.main``). Requiring a strict common prefix would stop
    at ``app`` and show a single `pipeline` box, so this follows the dominant
    group instead: a prefix covering most modules, exposing at least three
    segments.
    """
    split = [name.split(".") for name in names if "." in name]
    if not split:
        return ""
    total = len(split)
    depth_limit = max(len(parts) for parts in split)
    best = ""
    for depth in range(1, depth_limit):
        prefixes = Counter(".".join(parts[:depth]) for parts in split if len(parts) >= depth)
        prefix, covered = prefixes.most_common(1)[0]
        if covered < total * 0.9:
            break
        members = [parts for parts in split if parts[:depth] == prefix.split(".")]
        segments = {parts[depth] for parts in members if len(parts) > depth}
        if len(segments) >= 3:
            best = prefix
    return best


def _segments(nodes: list[Node]) -> list[str]:
    return sorted({segment(node.id) for node in nodes})


def _condense(segments: list[str], edges: list[Edge]) -> dict[str, int]:
    """Rank each segment so a dependency points from a higher rank to a lower one."""
    graph: dict[str, set[str]] = defaultdict(set)
    for edge in edges:
        source, target = segment(edge.src), segment(edge.dst)
        if source != target:
            graph[source].add(target)

    index: dict[str, int] = {}
    low: dict[str, int] = {}
    stack: list[str] = []
    on_stack: set[str] = set()
    components: list[list[str]] = []
    counter = [0]

    def visit(vertex: str) -> None:
        index[vertex] = low[vertex] = counter[0]
        counter[0] += 1
        stack.append(vertex)
        on_stack.add(vertex)
        for neighbour in graph.get(vertex, ()):  # noqa: B007
            if neighbour not in index:
                visit(neighbour)
                low[vertex] = min(low[vertex], low[neighbour])
            elif neighbour in on_stack:
                low[vertex] = min(low[vertex], index[neighbour])
        if low[vertex] == index[vertex]:
            component: list[str] = []
            while True:
                member = stack.pop()
                on_stack.discard(member)
                component.append(member)
                if member == vertex:
                    break
            components.append(component)

    for value in segments:
        if value not in index:
            visit(value)

    component_of: dict[str, int] = {}
    for at, component in enumerate(components):
        for member in component:
            component_of[member] = at

    depends: dict[int, set[int]] = defaultdict(set)
    for source, targets in graph.items():
        for target in targets:
            if component_of[source] != component_of[target]:
                depends[component_of[source]].add(component_of[target])

    rank_of_component: dict[int, int] = {}

    def rank(component: int) -> int:
        if component in rank_of_component:
            return rank_of_component[component]
        rank_of_component[component] = 0
        result = 0
        for target in depends.get(component, ()):
            result = max(result, rank(target) + 1)
        rank_of_component[component] = result
        return result

    return {value: rank(component_of[value]) for value in segments}


def derive_levels(nodes: list[Node], edges: list[Edge]) -> list[list[str]]:
    """Group segments by rank: inner (depended upon) first."""
    ranks = _condense(_segments(nodes), edges)
    if not ranks:
        return []
    depth = max(ranks.values()) + 1
    levels: list[list[str]] = [[] for _ in range(depth)]
    for name, value in sorted(ranks.items()):
        levels[value].append(name)
    return [level for level in levels if level]


def derive_foreign(nodes: list[Node], edges: list[Edge], known: set[str]) -> list[str]:
    """Not used yet: foreign libraries come from the scanner, not the model."""
    return []


def initial_policy(
    title: str, root: str, nodes: list[Node], edges: list[Edge], foreign: list[str]
) -> Policy:
    prefix = derive_prefix([node.ns for node in nodes])
    segments = _segments(nodes)
    order = sorted(segments, key=lambda name: (name not in edges, name))
    levels = derive_levels(nodes, edges)
    ranked = {name for level in levels for name in level}
    order = [name for level in levels for name in sorted(level)]
    order += sorted(set(segments) - ranked)
    return Policy(
        title=title,
        root=root,
        prefix=prefix,
        order=order,
        levels=levels,
        foreign=sorted(foreign),
    )
