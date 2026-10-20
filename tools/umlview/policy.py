"""The policy: what the diagram is allowed to say, and the dependency rule."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from model import KIND_DEPENDENCY, Edge, Node


class PolicyError(RuntimeError):
    """The policy is missing or malformed."""


@dataclass
class Policy:
    """Namespaces only. The diagram is generated; the policy only orders it."""

    title: str = ""
    root: str = "."
    prefix: str = ""
    order: list[str] = field(default_factory=list)
    levels: list[list[str]] = field(default_factory=list)
    foreign: list[str] = field(default_factory=list)
    edge_kinds: dict[str, str] = field(default_factory=dict)
    omit: list[str] = field(default_factory=list)
    omit_edges: list[list[str]] = field(default_factory=list)
    proposals: list[dict] = field(default_factory=list)
    packages: list[dict] = field(default_factory=list)
    diagrams: list[dict] = field(default_factory=list)
    hierarchical: bool = False

    @property
    def is_hierarchical(self) -> bool:
        """True when this is a namespace tree, not invented packages."""
        return self.hierarchical or (not self.packages and not self.diagrams)

    @classmethod
    def read(cls, path: Path) -> Policy:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as error:
            raise PolicyError(f"cannot read policy {path}: {error}") from error
        known = {field_name for field_name in cls.__dataclass_fields__}
        return cls(**{key: value for key, value in data.items() if key in known})

    def write(self, path: Path) -> None:
        payload = {
            "title": self.title,
            "root": self.root,
            "prefix": self.prefix,
            "order": self.order,
            "levels": self.levels,
            "foreign": self.foreign,
            "edge_kinds": self.edge_kinds,
            "omit": self.omit,
            "omit_edges": self.omit_edges,
            "proposals": self.proposals,
            "packages": self.packages,
            "diagrams": self.diagrams,
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def segment(module_id: str) -> str:
    """The first dotted part, which is the component a proposal refers to."""
    return module_id.split(".", 1)[0]


def ranks(levels: list[list[str]]) -> dict[str, int]:
    """Top-level segment -> rank. Smaller is inner, exactly as the original."""
    table: dict[str, int] = {}
    for value, group in enumerate(levels):
        for name in group:
            table[name] = value
    return table


def rank_of(node_id: str, table: dict[str, int]) -> int | None:
    """Rank for an id: the exact key, else the longest dotted prefix."""
    parts = node_id.split(".")
    for depth in range(len(parts), 0, -1):
        found = table.get(".".join(parts[:depth]))
        if found is not None:
            return found
    return None


def omitted(node_id: str, omit: list[str]) -> bool:
    """True when the id is listed in omit or sits under a listed component."""
    return any(
        node_id == entry or node_id.startswith(entry + ".") for entry in omit
    )


def apply_edge_kinds(edges: list[Edge], edge_kinds: dict[str, str]) -> None:
    """Rewrite a parser kind from the policy's ``from->to`` table."""
    for edge in edges:
        override = edge_kinds.get(f"{edge.src}->{edge.dst}")
        if override:
            edge.kind = override


def validate(
    nodes: list[Node], edges: list[Edge], levels: list[list[str]]
) -> list[Edge]:
    """Mark violating dependency edges, exactly as the original does.

    A dependency violates when both ends have a rank and the source rank is
    strictly smaller than the target rank. Same rank is allowed; any other
    kind is never compared. Hierarchical policies place every namespace in the
    tree, so the original reports no unassigned classes for them.
    """
    table = ranks(levels)
    violations: list[Edge] = []
    for edge in edges:
        edge.violating = False
        if edge.kind != KIND_DEPENDENCY:
            continue
        source_rank = rank_of(edge.src, table)
        target_rank = rank_of(edge.dst, table)
        if source_rank is None or target_rank is None:
            continue
        if source_rank < target_rank:
            edge.violating = True
            violations.append(edge)
    violations.sort(key=lambda edge: (edge.src, edge.dst))
    return violations
