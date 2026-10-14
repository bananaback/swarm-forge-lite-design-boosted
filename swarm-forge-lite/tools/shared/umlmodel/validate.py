"""Validate a model against the invariants of the uml-model format.

The rules come from `reference/model-format.md`. An error blocks a write. A
warning is reported and allowed, because upstream reports such a model too.
"""

from __future__ import annotations

import re

STEREOTYPES = ("class", "interface", "abstract", "enum")
KINDS = (
    "inheritance",
    "implements",
    "association",
    "dependency",
    "aggregation",
    "composition",
)
DIRECTIONS = ("tb", "lr")

ERROR = "error"
WARNING = "warning"

# A class id is a namespace: `component.Name`, at least one dot, no blank segment.
_ID = re.compile(r"^[A-Za-z0-9_-]+(\.[A-Za-z0-9_-]+)+$")


def finding(severity: str, code: str, message: str) -> dict:
    return {"severity": severity, "code": code, "message": message}


def packages(model: dict) -> list:
    return list(model.get("packages") or [])


def classes(model: dict) -> list:
    return [cls for pkg in packages(model) for cls in (pkg.get("classes") or [])]


def class_ids(model: dict) -> list:
    return [str(cls.get("id")) for cls in classes(model)]


def class_index(model: dict) -> dict:
    return {str(cls.get("id")): cls for cls in classes(model)}


def edges(model: dict) -> list:
    return list(model.get("edges") or [])


def foreign_ids(model: dict) -> list:
    """The ids of the `foreign` list, in the order the list gives them."""
    out = []
    for item in model.get("foreign") or []:
        if isinstance(item, str):
            out.append(item)
        elif isinstance(item, dict) and item.get("id"):
            out.append(str(item["id"]))
    return out


def level_segments(model: dict) -> list:
    segments = []
    for group in model.get("levels") or []:
        if isinstance(group, list):
            segments.extend(str(segment) for segment in group)
    return segments


def endpoint_resolves(endpoint: str, ids, prefixes) -> bool:
    """True when an endpoint names a class, a foreign id, or an id under one."""
    if endpoint in ids:
        return True
    return any(
        endpoint == prefix or endpoint.startswith(prefix + ".") for prefix in prefixes
    )


def findings(model: dict) -> list:
    """Every finding, errors first, in a stable order."""
    out: list[dict] = []
    _check_packages(model, out)
    _check_classes(model, out)
    _check_direction(model, out)
    _check_levels(model, out)
    _check_edges(model, out)
    _check_unassigned(model, out)
    order = {ERROR: 0, WARNING: 1}
    out.sort(key=lambda item: (order[item["severity"]], item["code"], item["message"]))
    return out


def _check_packages(model: dict, out: list) -> None:
    for pkg in model.get("packages") or []:
        if not isinstance(pkg, dict):
            out.append(finding(ERROR, "bad-package", "a package is not an object"))
            continue
        if not pkg.get("id"):
            out.append(finding(ERROR, "bad-package", "a package has no id"))
        if not pkg.get("label"):
            out.append(
                finding(ERROR, "bad-package", f"package {pkg.get('id')!r} has no label")
            )


def _check_classes(model: dict, out: list) -> None:
    seen: set[str] = set()
    for cls in classes(model):
        cid = str(cls.get("id"))
        if not _ID.match(cid):
            out.append(
                finding(ERROR, "bad-id", f"class id {cid!r} is not component.Name")
            )
        if cid in seen:
            out.append(finding(ERROR, "dup-id", f"duplicate class id {cid!r}"))
        seen.add(cid)
        stereotype = cls.get("stereotype")
        if stereotype is not None and stereotype not in STEREOTYPES:
            out.append(
                finding(ERROR, "bad-stereotype", f"{cid}: stereotype {stereotype!r}")
            )


def _check_direction(model: dict, out: list) -> None:
    direction = model.get("direction")
    if direction is not None and direction not in DIRECTIONS:
        out.append(finding(ERROR, "bad-direction", f"direction {direction!r}"))


def _check_levels(model: dict, out: list) -> None:
    for group in model.get("levels") or []:
        if not isinstance(group, list) or not group:
            out.append(
                finding(ERROR, "bad-levels", "a levels group is not a non-empty list")
            )


def _check_edges(model: dict, out: list) -> None:
    ids = set(class_ids(model))
    prefixes = foreign_ids(model)
    for edge in edges(model):
        if not isinstance(edge, dict):
            out.append(finding(ERROR, "bad-edge", "an edge is not an object"))
            continue
        for side in ("from", "to"):
            endpoint = edge.get(side)
            if not endpoint:
                out.append(finding(ERROR, "bad-edge", f"an edge has no {side}"))
            elif not endpoint_resolves(str(endpoint), ids, prefixes):
                out.append(
                    finding(
                        ERROR, "bad-edge", f"an edge names unknown {side} {endpoint!r}"
                    )
                )
        kind = edge.get("kind")
        if kind is not None and kind not in KINDS:
            out.append(finding(ERROR, "bad-kind", f"edge kind {kind!r}"))


def _check_unassigned(model: dict, out: list) -> None:
    known = set(level_segments(model))
    for cls in classes(model):
        first = str(cls.get("id", "")).split(".")[0]
        if first and first not in known:
            out.append(
                finding(WARNING, "unassigned", f"{cls.get('id')} is under no level")
            )


def errors(model: dict) -> list:
    return [item for item in findings(model) if item["severity"] == ERROR]


def warnings(model: dict) -> list:
    return [item for item in findings(model) if item["severity"] == WARNING]
