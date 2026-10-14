"""The read-only queries of the uml model tool.

Every handler returns `(data, text)`: `data` is the compact JSON payload and
`text` is the human-readable CLI form. A handler never writes the model.
"""

from __future__ import annotations

import json

from . import policy, validate
from .errors import UmlModelError
from .validate import (
    class_index,
    classes,
    edges,
    endpoint_resolves,
    foreign_ids,
    packages,
    warnings,
)


def _class_row(pkg: dict, cls: dict) -> dict:
    annotations = cls.get("annotations") or {}
    return {
        "id": cls.get("id"),
        "name": cls.get("name"),
        "stereotype": cls.get("stereotype") or "class",
        "package": pkg.get("id"),
        "level": cls.get("level"),
        "fields": len(cls.get("fields") or []),
        "ops": len(cls.get("ops") or []),
        "core": annotations.get("core"),
    }


def _lines(header: str, rows: list[str]) -> str:
    body = "\n".join(rows)
    return f"{header}\n{body}" if body else f"{header}\n(none)"


def q_classes(model: dict, params: dict) -> tuple[dict, str]:
    """Every class, with its package and its member counts."""
    rows = [
        _class_row(pkg, cls)
        for pkg in packages(model)
        for cls in (pkg.get("classes") or [])
    ]
    wanted = params.get("package")
    if wanted:
        rows = [row for row in rows if row["package"] == wanted]
    text_rows = [
        f"{row['id']:<34} {row['stereotype']:<10} {row['package']:<16}"
        f" fields={row['fields']} ops={row['ops']}"
        for row in rows
    ]
    return {"count": len(rows), "rows": rows}, _lines(
        f"classes ({len(rows)})", text_rows
    )


def q_class(model: dict, params: dict) -> tuple[dict, str]:
    """One class, in full."""
    cid = _require(params, "id")
    cls = class_index(model).get(cid)
    if cls is None:
        raise UmlModelError(f"no such class: {cid}")
    return {"class": cls, "id": cid}, json.dumps(cls, indent=2, ensure_ascii=False)


def q_ops(model: dict, params: dict) -> tuple[dict, str]:
    """The ops of one class, with the contract annotations."""
    cid = _require(params, "id")
    cls = class_index(model).get(cid)
    if cls is None:
        raise UmlModelError(f"no such class: {cid}")
    rows = []
    for op in cls.get("ops") or []:
        annotations = op.get("annotations") or {}
        rows.append(
            {
                "name": op.get("name"),
                "returns": op.get("returns"),
                "cqs": annotations.get("cqs"),
                "pre": annotations.get("pre"),
                "post": annotations.get("post"),
                "invariant": annotations.get("invariant"),
                "visibility": annotations.get("visibility"),
            }
        )
    text_rows = [
        f"{row['name']:<18} {row['cqs'] or 'query'!s:<9} returns={row['returns']}"
        for row in rows
    ]
    return {"count": len(rows), "rows": rows}, _lines(
        f"ops of {cid} ({len(rows)})", text_rows
    )


def q_packages(model: dict, params: dict) -> tuple[dict, str]:
    """Every package, with its class count."""
    rows = [
        {
            "id": pkg.get("id"),
            "label": pkg.get("label"),
            "classes": len(pkg.get("classes") or []),
        }
        for pkg in packages(model)
    ]
    text_rows = [
        f"{row['id']!s:<20} classes={row['classes']:<3} {row['label']}" for row in rows
    ]
    return {"count": len(rows), "rows": rows}, _lines(
        f"packages ({len(rows)})", text_rows
    )


def q_levels(model: dict, params: dict) -> tuple[dict, str]:
    """The level groups, inner first, with their rank."""
    groups = model.get("levels") or []
    rows = [
        {"rank": rank, "segments": [str(segment) for segment in group]}
        for rank, group in enumerate(groups)
        if isinstance(group, list)
    ]
    text_rows = [f"{row['rank']:>2}  {', '.join(row['segments'])}" for row in rows]
    return {"count": len(rows), "rows": rows}, _lines(
        f"levels ({len(rows)})", text_rows
    )


def q_edges(model: dict, params: dict) -> tuple[dict, str]:
    """Every edge, in file order."""
    rows = [
        {
            "from": edge.get("from"),
            "to": edge.get("to"),
            "kind": edge.get("kind") or "association",
            "label": edge.get("label"),
        }
        for edge in edges(model)
    ]
    text_rows = [
        f"{row['from']!s:<34} -> {row['to']!s:<34} {row['kind']}" for row in rows
    ]
    return {"count": len(rows), "rows": rows}, _lines(f"edges ({len(rows)})", text_rows)


def q_edges_of(model: dict, params: dict) -> tuple[dict, str]:
    """The edges that name one class on either end."""
    cid = _require(params, "id")
    rows = [
        {
            "from": edge.get("from"),
            "to": edge.get("to"),
            "kind": edge.get("kind") or "association",
            "direction": "out" if edge.get("from") == cid else "in",
        }
        for edge in edges(model)
        if edge.get("from") == cid or edge.get("to") == cid
    ]
    text_rows = [
        f"{row['direction']:<4} {row['from']} -> {row['to']} ({row['kind']})"
        for row in rows
    ]
    return {"count": len(rows), "rows": rows}, _lines(
        f"edges of {cid} ({len(rows)})", text_rows
    )


def q_violations(model: dict, params: dict) -> tuple[dict, str]:
    """The dependency edges that run from an inner rank to an outer rank."""
    rows = policy.violations(model)
    text_rows = [
        f"{row['from']} (rank {row['from_rank']}) ->"
        f" {row['to']} (rank {row['to_rank']})"
        for row in rows
    ]
    return {"count": len(rows), "rows": rows}, _lines(
        f"violations ({len(rows)})", text_rows
    )


def q_unassigned(model: dict, params: dict) -> tuple[dict, str]:
    """The classes whose first id segment is under no level."""
    rows = [
        {"id": item["message"].split(" ")[0], "message": item["message"]}
        for item in warnings(model)
        if item["code"] == "unassigned"
    ]
    text_rows = [row["message"] for row in rows]
    return {"count": len(rows), "rows": rows}, _lines(
        f"unassigned ({len(rows)})", text_rows
    )


def _duplicate_ids(model: dict) -> list:
    seen: set[str] = set()
    dup: list[str] = []
    for pkg in packages(model):
        for cls in pkg.get("classes") or []:
            cid = str(cls.get("id"))
            if cid in seen and cid not in dup:
                dup.append(cid)
            seen.add(cid)
    return dup


def q_dups(model: dict, params: dict) -> tuple[dict, str]:
    """The duplicate class ids."""
    rows = [{"id": cid} for cid in _duplicate_ids(model)]
    text_rows = [row["id"] for row in rows]
    return {"count": len(rows), "rows": rows}, _lines(
        f"duplicate ids ({len(rows)})", text_rows
    )


def q_bad_edges(model: dict, params: dict) -> tuple[dict, str]:
    """The edges whose endpoint names no class and no foreign id."""
    ids = {str(cls.get("id")) for cls in classes(model)}
    prefixes = foreign_ids(model)
    rows = []
    for edge in edges(model):
        for side in ("from", "to"):
            endpoint = str(edge.get(side))
            if not endpoint_resolves(endpoint, ids, prefixes):
                rows.append(
                    {
                        "from": edge.get("from"),
                        "to": edge.get("to"),
                        "side": side,
                        "endpoint": endpoint,
                    }
                )
    text_rows = [
        f"{row['from']} -> {row['to']} (unknown {row['side']} {row['endpoint']})"
        for row in rows
    ]
    return {"count": len(rows), "rows": rows}, _lines(
        f"bad edges ({len(rows)})", text_rows
    )


def q_orphans(model: dict, params: dict) -> tuple[dict, str]:
    """The classes that no edge names on either end."""
    touched: set[str] = set()
    for edge in edges(model):
        touched.add(str(edge.get("from")))
        touched.add(str(edge.get("to")))
    rows = [
        {"id": cls.get("id")}
        for cls in classes(model)
        if str(cls.get("id")) not in touched
    ]
    text_rows = [f"{row['id']}" for row in rows]
    return {"count": len(rows), "rows": rows}, _lines(
        f"orphans ({len(rows)})", text_rows
    )


def q_annotations(model: dict, params: dict) -> tuple[dict, str]:
    """The annotation keys in use, and how many members carry each."""
    counts: dict[str, int] = {}
    for cls in classes(model):
        for key in cls.get("annotations") or {}:
            counts[f"class.{key}"] = counts.get(f"class.{key}", 0) + 1
        for op in cls.get("ops") or []:
            for key in op.get("annotations") or {}:
                counts[f"op.{key}"] = counts.get(f"op.{key}", 0) + 1
    rows = [{"key": key, "count": counts[key]} for key in sorted(counts)]
    text_rows = [f"{row['key']:<20} {row['count']}" for row in rows]
    return {"count": len(rows), "rows": rows}, _lines(
        f"annotation keys ({len(rows)})", text_rows
    )


def q_check(model: dict, params: dict) -> tuple[dict, str]:
    """Validate the model and list every error and warning.

    An error sets the exit code. A warning (a class under no level) does not.
    """
    items = validate.findings(model)
    errors = [item for item in items if item["severity"] == "error"]
    warnings_ = [item for item in items if item["severity"] == "warning"]
    rows = [
        {
            "severity": item["severity"],
            "code": item["code"],
            "message": item["message"],
        }
        for item in items
    ]
    text_rows = [
        f"{row['severity']:<7} {row['code']:<14} {row['message']}" for row in rows
    ]
    data = {"errors": len(errors), "warnings": len(warnings_), "rows": rows}
    header = f"check ({len(errors)} error(s), {len(warnings_)} warning(s))"
    return data, _lines(header, text_rows)


def q_stats(model: dict, params: dict) -> tuple[dict, str]:
    """A one-screen summary of the model."""
    all_classes = classes(model)
    ops = [op for cls in all_classes for op in (cls.get("ops") or [])]
    fields = [field for cls in all_classes for field in (cls.get("fields") or [])]
    data = {
        "title": model.get("title"),
        "direction": model.get("direction") or "tb",
        "packages": len(packages(model)),
        "classes": len(all_classes),
        "ops": len(ops),
        "fields": len(fields),
        "edges": len(edges(model)),
        "levels": len(model.get("levels") or []),
        "foreign": len(model.get("foreign") or []),
        "violations": len(policy.violations(model)),
        "unassigned": len(
            [item for item in warnings(model) if item["code"] == "unassigned"]
        ),
    }
    text = "\n".join(f"{key:<12} {value}" for key, value in data.items())
    return data, text


def _require(params: dict, name: str):
    value = params.get(name)
    if value is None or value == "":
        raise UmlModelError(f"pass --{name}")
    return value
