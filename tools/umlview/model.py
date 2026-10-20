"""The generated diagram model: modules, edges, and graded functions."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path

KIND_DEPENDENCY = "dependency"
KIND_ASSOCIATION = "association"
KIND_IMPLEMENTS = "implements"

# Strongest wins when several kinds share one endpoint pair, exactly as the
# original's kind-rank table.
KIND_RANK = {
    "implements": 4,
    "inheritance": 4,
    "composition": 3,
    "aggregation": 2,
    "association": 1,
    "dependency": 0,
}

# Grading cutoffs, copied from uml-viewer.domain.config.
CRAP_GREEN = 8.0
CRAP_YELLOW = 12.0
CRAP_RED = 20.0
GRADE_BEST = 10.0
GRADE_MID = 5.5
GRADE_WORST = 1.0
MUTATION_RED = 0.80
MUTATION_YELLOW = 0.90
MUTATION_GREEN = 1.00


@dataclass(frozen=True)
class Summary:
    """A pooled CRAP sample: function count, mean, population sigma, worst."""

    n: int
    mu: float
    sigma: float
    max: float

    def as_json(self) -> dict:
        return {"n": self.n, "mu": self.mu, "sigma": self.sigma, "max": self.max}

    @classmethod
    def from_json(cls, data: dict) -> Summary:
        return cls(
            n=int(data["n"]),
            mu=float(data["mu"]),
            sigma=float(data.get("sigma", 0.0)),
            max=float(data.get("max", data["mu"])),
        )


@dataclass(frozen=True)
class Op:
    """One function or method, as metrics report it."""

    name: str
    cc: int | None = None
    coverage: float | None = None
    crap: float | None = None

    def as_json(self) -> dict:
        return {
            "name": self.name,
            "cc": self.cc,
            "coverage": self.coverage,
            "crap": self.crap,
        }

    @classmethod
    def from_json(cls, data: dict) -> Op:
        return cls(
            name=data["name"],
            cc=data.get("cc"),
            coverage=data.get("coverage"),
            crap=data.get("crap"),
        )


@dataclass
class Node:
    """One module. The id is the namespace path with the policy prefix removed."""

    id: str
    ns: str
    name: str
    ops: list[Op] = field(default_factory=list)
    cc: int | None = None
    coverage: float | None = None
    crap: float | None = None
    summary: Summary | None = None
    foreign: bool = False
    killed: int = 0
    survived: int = 0
    uncovered: int | None = None
    sites: int = 0
    mut_gap: int = 0
    fields: list[str] = field(default_factory=list)

    def as_json(self) -> dict:
        return {
            "id": self.id,
            "ns": self.ns,
            "name": self.name,
            "cc": self.cc,
            "coverage": self.coverage,
            "crap": self.crap,
            "summary": self.summary.as_json() if self.summary else None,
            "foreign": self.foreign,
            "killed": self.killed,
            "survived": self.survived,
            "uncovered": self.uncovered,
            "sites": self.sites,
            "gap": self.mut_gap,
            "fields": list(self.fields),
            "ops": [op.as_json() for op in self.ops],
        }

    @classmethod
    def from_json(cls, data: dict) -> Node:
        return cls(
            id=data["id"],
            ns=data["ns"],
            name=data["name"],
            cc=data.get("cc"),
            coverage=data.get("coverage"),
            crap=data.get("crap"),
            summary=Summary.from_json(data["summary"]) if data.get("summary") else None,
            foreign=bool(data.get("foreign", False)),
            killed=int(data.get("killed", 0)),
            survived=int(data.get("survived", 0)),
            uncovered=data.get("uncovered"),
            sites=int(data.get("sites", 0)),
            mut_gap=int(data.get("gap", 0)),
            fields=list(data.get("fields", [])),
            ops=[Op.from_json(op) for op in data.get("ops", [])],
        )


@dataclass
class Package:
    """A named box holding classes: the static-diagram form."""

    id: str
    label: str
    classes: list[Node] = field(default_factory=list)

    def as_json(self) -> dict:
        return {
            "id": self.id,
            "label": self.label,
            "classes": [node.as_json() for node in self.classes],
        }

    @classmethod
    def from_json(cls, data: dict) -> Package:
        return cls(
            id=data["id"],
            label=data.get("label", data["id"]),
            classes=[Node.from_json(node) for node in data.get("classes", [])],
        )


@dataclass
class Edge:
    """One dependency between two module ids."""

    src: str
    dst: str
    kind: str = KIND_DEPENDENCY
    violating: bool = False

    def as_json(self) -> dict:
        return {
            "from": self.src,
            "to": self.dst,
            "kind": self.kind,
            "violating": self.violating,
        }

    @classmethod
    def from_json(cls, data: dict) -> Edge:
        return cls(
            src=data["from"],
            dst=data["to"],
            kind=data.get("kind", KIND_DEPENDENCY),
            violating=bool(data.get("violating", False)),
        )


@dataclass
class Model:
    """The whole generated diagram."""

    title: str
    prefix: str
    nodes: list[Node] = field(default_factory=list)
    edges: list[Edge] = field(default_factory=list)
    foreign: list[str] = field(default_factory=list)
    order: list[str] = field(default_factory=list)
    levels: list[list[str]] = field(default_factory=list)
    unassigned: list[str] = field(default_factory=list)
    mode: str = "hierarchy"
    packages: list[Package] = field(default_factory=list)
    foreign_classes: list[Node] = field(default_factory=list)
    mutation_present: bool = False

    def index(self) -> dict[str, Node]:
        return {node.id: node for node in self.nodes}

    def as_json(self) -> dict:
        return {
            "title": self.title,
            "prefix": self.prefix,
            "nodes": [node.as_json() for node in self.nodes],
            "edges": [edge.as_json() for edge in self.edges],
            "foreign": list(self.foreign),
            "order": list(self.order),
            "levels": [list(level) for level in self.levels],
            "unassigned": list(self.unassigned),
            "mode": self.mode,
            "packages": [package.as_json() for package in self.packages],
            "foreign_classes": [node.as_json() for node in self.foreign_classes],
            "mutation_present": self.mutation_present,
        }

    def to_path(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(self.as_json(), indent=1, sort_keys=False) + "\n",
            encoding="utf-8",
        )

    @classmethod
    def from_json(cls, data: dict) -> Model:
        return cls(
            title=data.get("title", ""),
            prefix=data.get("prefix", ""),
            nodes=[Node.from_json(node) for node in data.get("nodes", [])],
            edges=[Edge.from_json(edge) for edge in data.get("edges", [])],
            foreign=list(data.get("foreign", [])),
            order=list(data.get("order", [])),
            levels=[list(level) for level in data.get("levels", [])],
            unassigned=list(data.get("unassigned", [])),
            mode=data.get("mode", "hierarchy"),
            packages=[Package.from_json(package) for package in data.get("packages", [])],
            foreign_classes=[
                Node.from_json(node) for node in data.get("foreign_classes", [])
            ],
            mutation_present=bool(data.get("mutation_present", False)),
        )

    @classmethod
    def read(cls, path: Path) -> Model:
        return cls.from_json(json.loads(path.read_text(encoding="utf-8")))


def validate_model(model: Model) -> list[str]:
    """The original's IR checks: unique ids, known endpoints, sane ranges."""
    errors: list[str] = []
    seen: set[str] = set()
    classes = (
        [node for package in model.packages for node in package.classes]
        if model.packages
        else list(model.nodes)
    )
    for node in classes:
        if node.id in seen:
            errors.append(f"duplicate class id: {node.id}")
        seen.add(node.id)
        if node.coverage is not None and not 0.0 <= node.coverage <= 1.0:
            errors.append(f"coverage out of range on {node.id}: {node.coverage}")
        if node.cc is not None and node.cc < 0:
            errors.append(f"negative cc on {node.id}: {node.cc}")
        for op in node.ops:
            if op.coverage is not None and not 0.0 <= op.coverage <= 1.0:
                errors.append(f"coverage out of range on {node.id}:{op.name}")
    for package in model.packages:
        if not package.label:
            errors.append(f"package needs a label: {package.id}")
    known = seen | {node.id for node in model.foreign_classes}
    for edge in model.edges:
        if edge.src not in known:
            errors.append(f"edge from unknown class {edge.src}")
        if edge.dst not in known:
            errors.append(f"edge to unknown class {edge.dst}")
    return errors


def round1(value: float) -> float:
    """Nearest tenth, rounding halves up like the original's Math/round."""
    return math.floor(value * 10.0 + 0.5) / 10.0


def summarize(scores: list[float]) -> Summary | None:
    """Function count, mean, population sigma, and max of CRAP scores."""
    values = [float(score) for score in scores]
    if not values:
        return None
    count = len(values)
    mu = sum(values) / count
    variance = sum((value - mu) ** 2 for value in values) / count
    return Summary(
        n=count,
        mu=round1(mu),
        sigma=round1(math.sqrt(variance)),
        max=round1(max(values)),
    )


def combine(summaries: list[Summary]) -> Summary | None:
    """Function-weighted pooling, identical to the original's combine-groups."""
    groups = [group for group in summaries if group and group.n > 0]
    if not groups:
        return None
    n = sum(group.n for group in groups)
    weighted = sum(group.n * group.mu for group in groups)
    squares = sum(group.n * (group.sigma**2 + group.mu**2) for group in groups)
    mu = weighted / n
    variance = max(0.0, squares / n - mu**2)
    return Summary(
        n=n,
        mu=round1(mu),
        sigma=round1(math.sqrt(variance)),
        max=round1(max(group.max for group in groups)),
    )


def crap_risk(summary: Summary | None) -> float | None:
    """The CRAP score a box is graded by: mean plus sigma."""
    if summary is None:
        return None
    return summary.mu + summary.sigma


def _along(x: float, x0: float, x1: float, x2: float, y0: float, y1: float, y2: float) -> float:
    if x <= x0:
        return y0
    if x <= x1:
        return y0 + (x - x0) / (x1 - x0) * (y1 - y0) if x1 != x0 else y0
    if x <= x2:
        return y1 + (x - x1) / (x2 - x1) * (y2 - y1) if x2 != x1 else y1
    return y2


def crap_grade(score: float | None) -> float:
    """CRAP μ+σ on the 1..10 scale. Missing counts as red (1)."""
    if score is None:
        return GRADE_WORST
    return _along(
        float(score),
        CRAP_GREEN,
        CRAP_YELLOW,
        CRAP_RED,
        GRADE_BEST,
        GRADE_MID,
        GRADE_WORST,
    )


@dataclass
class Document:
    """One or more stacked diagrams, exactly the original's document shape."""

    title: str
    diagrams: list[Model] = field(default_factory=list)

    def as_json(self) -> dict:
        return {"title": self.title, "diagrams": [item.as_json() for item in self.diagrams]}

    @classmethod
    def from_json(cls, data: dict) -> Document:
        return cls(
            title=data.get("title", "UML"),
            diagrams=[Model.from_json(item) for item in data.get("diagrams", [])],
        )

    @classmethod
    def read(cls, path: Path) -> Document:
        data = json.loads(path.read_text(encoding="utf-8"))
        if "diagrams" in data:
            return cls.from_json(data)
        return cls(title=data.get("title", "UML"), diagrams=[Model.from_json(data)])

    def to_path(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.as_json(), indent=1) + "\n", encoding="utf-8")


def mutation_ratio(node: Node) -> float | None:
    """Killed / (killed + survived + gap), nil when nothing was measured."""
    n = node.killed + node.survived + node.mut_gap
    return node.killed / n if n > 0 else None


def mutation_grade(score: float | None) -> float:
    """Mutation ratio on 1..10. Missing counts as red (1)."""
    if score is None:
        return GRADE_WORST
    return _along(score, MUTATION_RED, MUTATION_YELLOW, MUTATION_GREEN,
                  GRADE_WORST, GRADE_MID, GRADE_BEST)


def combined_grade(crap: float, mutation: float) -> float:
    """Average of the present grades, exactly the original's combined-grade."""
    grades = [value for value in (crap, mutation) if value is not None]
    return sum(grades) / len(grades) if grades else GRADE_WORST


def grade(value: float | None) -> float:
    """Backwards-compatible alias: grade a CRAP μ+σ score."""
    return crap_grade(value)
