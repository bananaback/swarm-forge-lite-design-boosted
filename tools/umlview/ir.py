"""Load a hand-authored IR, EDN or JSON, and normalize it like the original.

The original accepts a static diagram with ``:packages`` (and ``:diagrams``);
this reads that shape, keeps the same normalization and range rules, and builds
the same Model the generated path produces.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from edn import loads
from model import Document, Edge, Model, Node, Op, Package, Summary


class IrError(RuntimeError):
    """The authored IR is malformed."""


def as_id(value) -> str:
    text = str(value)
    return re.sub(r"\s+", "-", text.lower())


def _as_crap(value) -> tuple[float | None, Summary | None]:
    if value is None:
        return None, None
    if isinstance(value, (int, float)):
        risk = float(value)
        return risk, Summary(n=1, mu=risk, sigma=0.0, max=risk)
    if isinstance(value, dict):
        mu = float(value["mu"])
        sigma = float(value.get("sigma", value.get("sd", 0)) or 0)
        maximum = float(value.get("max", mu))
        return mu + sigma, Summary(
            n=int(value.get("n", 1)), mu=mu, sigma=sigma, max=maximum
        )
    raise IrError(f"crap must be a number or {{mu, max, sigma}}, got {value!r}")


def _as_coverage(value) -> float | None:
    if value is None:
        return None
    number = float(value)
    if not 0.0 <= number <= 1.0:
        raise IrError(f"coverage must be between 0 and 1, got {value!r}")
    return number


def _as_member(value) -> Op:
    if isinstance(value, str):
        return Op(name=value)
    if isinstance(value, dict):
        name = value.get("name") or value.get("text") or ""
        risk, _ = _as_crap(value.get("crap"))
        return Op(
            name=str(name),
            cc=value.get("cc"),
            coverage=_as_coverage(value.get("coverage")),
            crap=risk,
        )
    raise IrError(f"member must be a string or map, got {value!r}")


def _as_class(value: dict) -> Node:
    name = value.get("name") or value.get("id")
    if not name:
        raise IrError(f"class needs a name or id: {value!r}")
    risk, summary = _as_crap(value.get("crap"))
    return Node(
        id=as_id(value.get("id") or name),
        ns=str(value.get("ns", "")),
        name=str(name),
        ops=[_as_member(op) for op in value.get("ops", [])],
        cc=value.get("cc"),
        coverage=_as_coverage(value.get("coverage")),
        fields=[str(member) for member in value.get("fields", [])],
        crap=risk,
        summary=summary,
    )


def _as_package(value: dict) -> Package:
    label = value.get("label") or value.get("id")
    if not label:
        raise IrError(f"package needs a label or id: {value!r}")
    return Package(
        id=as_id(value.get("id") or label),
        label=str(label),
        classes=[_as_class(item) for item in value.get("classes", [])],
    )


def _as_edge(value: dict) -> Edge:
    if not value.get("from") or not value.get("to"):
        raise IrError(f"edge needs from and to: {value!r}")
    return Edge(
        src=as_id(value["from"]),
        dst=as_id(value["to"]),
        kind=str(value.get("kind", "association")),
    )


def _model_from(raw: dict) -> Model:
    if not isinstance(raw, dict):
        raise IrError("a diagram must be a map")
    packages = [_as_package(item) for item in raw.get("packages") or []]
    edges = [_as_edge(item) for item in raw.get("edges") or []]
    foreign = [_as_class(item) for item in raw.get("foreign") or []]
    return Model(
        title=str(raw.get("title") or "UML"),
        prefix=str(raw.get("prefix") or ""),
        edges=edges,
        packages=packages,
        foreign_classes=foreign,
        mode="packages" if packages else "hierarchy",
    )


def load_document(path: Path) -> Document:
    """Read a document: one diagram, or a stack under :diagrams."""
    if not path.is_file():
        raise IrError(f"no IR at {path}")
    text = path.read_text(encoding="utf-8")
    raw = json.loads(text) if path.suffix == ".json" else loads(text)
    if not isinstance(raw, dict):
        raise IrError(f"{path} is not an IR map")
    title = str(raw.get("title") or "UML")
    if raw.get("diagrams"):
        return Document(title=title, diagrams=[_model_from(item) for item in raw["diagrams"]])
    return Document(title=title, diagrams=[_model_from(raw)])


def load(path: Path) -> Model:
    """The first diagram, matching the original's load-diagram."""
    return load_document(path).diagrams[0]
