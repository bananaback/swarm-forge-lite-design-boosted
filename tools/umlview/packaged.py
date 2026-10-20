"""Generate packaged diagrams: invented components over real namespaces.

Mirrors the original's non-hierarchical branch: one diagram per policy
``:diagrams`` entry, either an overview of every policy package or one package
with its neighbour stubs and referenced foreign ovals.
"""

from __future__ import annotations

from model import Document, Edge, Model, Node, Package
from policy import Policy


class PackagedError(RuntimeError):
    """A packaged diagram names something the policy cannot resolve."""


def nses(entry) -> list[str]:
    """Namespaces listed by a package layer entry (strings or {:nses [...]})."""
    if isinstance(entry, str):
        return [entry]
    if isinstance(entry, dict):
        found: list[str] = []
        for value in entry.get("nses", []):
            found.extend(nses(value))
        return found
    return []


def _lookup(index: dict[str, Node], class_id: str) -> Node | None:
    return index.get(class_id)


def _classes(index: dict[str, Node], ids: list[str]) -> list[Node]:
    return [index[value] for value in ids if value in index]


def _foreign_from(edges: list[Edge], ids: set[str], foreign: dict[str, Node]) -> list[Node]:
    wanted = {
        edge.dst
        for edge in edges
        if edge.src in ids and edge.dst in foreign
    }
    return [foreign[value] for value in sorted(wanted)]


def _edges_among(
    edges: list[Edge],
    ids: set[str],
    entry: dict,
    home: set[str] | None,
    omit_edges: list[list[str]] | None = None,
) -> list[Edge]:
    kept: list[Edge] = []
    for edge in edges:
        if edge.src not in ids or edge.dst not in ids:
            continue
        if home is not None and not (
            edge.src in home or edge.dst in home or edge.kind == "implements"
        ):
            continue
        kept.append(Edge(src=edge.src, dst=edge.dst, kind=edge.kind))
    omitted = {
        tuple(pair) for pair in (omit_edges or []) if len(pair) == 2
    } | {tuple(pair) for pair in (entry.get("omit_edges") or []) if len(pair) == 2}
    if omitted:
        kept = [edge for edge in kept if (edge.src, edge.dst) not in omitted]
    overrides = entry.get("edge_kinds") or {}
    for edge in kept:
        override = overrides.get(f"{edge.src}->{edge.dst}")
        if override:
            edge.kind = override
    return sorted(kept, key=lambda edge: (edge.src, edge.dst))


def _overview(
    policy: Policy,
    model: Model,
    entry: dict,
    index: dict[str, Node],
    foreign: dict[str, Node],
) -> Model:
    packages: list[Package] = []
    claimed: set[str] = set()
    for definition in policy.packages:
        members = [value for value in nses(definition) if value in index]
        claimed.update(members)
        packages.append(
            Package(
                id=str(definition.get("id", definition.get("label", ""))),
                label=str(definition.get("label", definition.get("id", ""))),
                classes=_classes(index, members),
            )
        )
    extra = sorted(
        node.id for node in model.nodes if node.id not in claimed and not node.foreign
    )
    if extra:
        packages.append(
            Package(id="unassigned", label="Unassigned", classes=_classes(index, extra))
        )
    ids = {node.id for package in packages for node in package.classes}
    ovals = _foreign_from(model.edges, ids, foreign)
    ids |= {node.id for node in ovals}
    return Model(
        title=str(entry.get("title") or policy.title or "UML"),
        prefix=policy.prefix,
        mode="packages",
        packages=packages,
        foreign_classes=ovals,
        edges=_edges_among(model.edges, ids, entry, None, policy.omit_edges),
    )


def _package(
    policy: Policy,
    model: Model,
    entry: dict,
    index: dict[str, Node],
    foreign: dict[str, Node],
) -> Model:
    wanted = str(entry.get("package", ""))
    definition = next(
        (item for item in policy.packages if str(item.get("id")) == wanted),
        None,
    )
    if definition is None:
        raise PackagedError(f"diagram package not in policy: {wanted}")
    home = {value for value in nses(definition) if value in index}
    neighbours = {
        edge.dst for edge in model.edges if edge.src in home and edge.dst not in home
    }
    stubs = sorted(value for value in neighbours if value in index)
    ovals = _foreign_from(model.edges, home, foreign)
    ids = home | set(stubs) | {node.id for node in ovals}
    classes = _classes(index, sorted(home) + stubs)
    return Model(
        title=str(entry.get("title") or policy.title or "UML"),
        prefix=policy.prefix,
        mode="packages",
        packages=[
            Package(
                id=str(definition.get("id", wanted)),
                label=str(definition.get("label", wanted)),
                classes=classes,
            )
        ],
        foreign_classes=ovals,
        edges=_edges_among(model.edges, ids, entry, home, policy.omit_edges),
    )


def build(policy: Policy, model: Model) -> Document:
    """One diagram per policy ``:diagrams`` entry, in order."""
    if not policy.diagrams:
        raise PackagedError("a packaged policy needs at least one :diagrams entry")
    index = {node.id: node for node in model.nodes}
    foreign = {node.id: node for node in model.foreign_classes}
    diagrams = []
    for entry in policy.diagrams:
        if not isinstance(entry, dict):
            raise PackagedError(f"diagram entry must be a map: {entry!r}")
        if entry.get("view") == "overview":
            diagrams.append(_overview(policy, model, entry, index, foreign))
        else:
            diagrams.append(_package(policy, model, entry, index, foreign))
    return Document(title=policy.title or "UML", diagrams=diagrams)
