"""The authored design overlay: objects that code does not have yet.

The overlay is the only stored design data. Everything else is scanned from the
code on every command, so the overlay is the only thing that can go stale — and
`diff`/`validate` name exactly which entry is stale and for how long.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

VALID_KINDS = ("extends", "implements", "composition", "aggregation", "dependency")
VALID_STEREOTYPES = ("class", "interface", "abstract", "enum", "data", "exception")


def load(path: Path) -> dict:
    if not path.is_file():
        return {"nodes": [], "edges": [], "annotations": {}}
    data = json.loads(path.read_text(encoding="utf-8"))
    data.setdefault("nodes", [])
    data.setdefault("edges", [])
    data.setdefault("annotations", {})
    return data


def save(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def today() -> str:
    return date.today().isoformat()


def add_node(data: dict, node: dict) -> None:
    data["nodes"] = [n for n in data["nodes"] if n["id"] != node["id"]]
    data["nodes"].append(node)


def remove_node(data: dict, node_id: str) -> bool:
    before = len(data["nodes"])
    data["nodes"] = [n for n in data["nodes"] if n["id"] != node_id]
    data["edges"] = [e for e in data["edges"] if node_id not in (e["from"], e["to"])]
    data["annotations"].pop(node_id, None)
    return len(data["nodes"]) != before


def add_edge(data: dict, edge: dict) -> None:
    data["edges"] = [e for e in data["edges"] if (e["from"], e["to"]) != (edge["from"], edge["to"])]
    data["edges"].append(edge)


def remove_edge(data: dict, source: str, target: str) -> bool:
    before = len(data["edges"])
    data["edges"] = [e for e in data["edges"] if (e["from"], e["to"]) != (source, target)]
    return len(data["edges"]) != before


def annotate(data: dict, class_id: str, note: str | None, layer: str | None) -> None:
    entry = data["annotations"].setdefault(class_id, {})
    if note is not None:
        entry["note"] = note
    if layer is not None:
        entry["layer"] = layer


def age_days(stamp: str) -> int:
    try:
        return (date.today() - date.fromisoformat(stamp)).days
    except ValueError:
        return -1


def diff(code_ids: set[str], code_edges: set[tuple[str, str]], data: dict) -> list[str]:
    rows = []
    for node in data["nodes"]:
        if node["id"] in code_ids:
            rows.append(f"stale overlay: {node['id']} now exists in code")
        else:
            rows.append(f"design-only: {node['id']} (since {node.get('since', '?')}, {age_days(node.get('since', ''))}d)")
    for edge in data["edges"]:
        pair = (edge["from"], edge["to"])
        if pair in code_edges:
            rows.append(f"stale overlay edge: {edge['from']} -> {edge['to']} now exists in code")
        else:
            rows.append(f"design-only edge: {edge['from']} -> {edge['to']} ({edge['kind']})")
    return rows


def validate(data: dict, code_ids: set[str], code_edges: set[tuple[str, str]], strict: bool = False) -> list[str]:
    problems = []
    ids = set(code_ids)
    for node in data["nodes"]:
        cid = node["id"]
        if cid in code_ids:
            problems.append(f"overlay node {cid} now exists in code; remove it")
        if node.get("stereotype", "class") not in VALID_STEREOTYPES:
            problems.append(f"overlay node {cid}: bad stereotype {node.get('stereotype')!r}")
        if node.get("layer", "core") not in ("core", "shell"):
            problems.append(f"overlay node {cid}: bad layer {node.get('layer')!r}")
        if not node.get("subsystem"):
            problems.append(f"overlay node {cid}: no subsystem")
        ids.add(cid)
    for edge in data["edges"]:
        if edge["kind"] not in VALID_KINDS:
            problems.append(f"overlay edge {edge['from']} -> {edge['to']}: bad kind {edge['kind']!r}")
        if edge["from"] not in ids:
            problems.append(f"overlay edge from unknown node {edge['from']}")
        if edge["to"] not in ids:
            problems.append(f"overlay edge to unknown node {edge['to']}")
        if (edge["from"], edge["to"]) in code_edges:
            problems.append(f"overlay edge {edge['from']} -> {edge['to']} now exists in code; remove it")
        age = age_days(edge.get("since", ""))
        if strict and age > 14:
            problems.append(f"overlay edge {edge['from']} -> {edge['to']} is {age}d old and still not implemented")
    return problems


def merge(classes: dict, edges: list[tuple[str, str, str]], data: dict, subsystem: str, make_class):
    """Fold the overlay entries of one subsystem into a scanned model."""
    for node in data["nodes"]:
        if node.get("subsystem") != subsystem:
            continue
        name = node["id"].rsplit(".", 1)[-1]
        if name in classes:
            continue
        classes[name] = make_class(node, name)
    known = set(classes)
    for edge in data["edges"]:
        src = edge["from"].rsplit(".", 1)[-1]
        dst = edge["to"].rsplit(".", 1)[-1]
        if src in known and dst in known:
            edges.append((src, dst, edge["kind"]))
    for class_id, meta in data.get("annotations", {}).items():
        name = class_id.rsplit(".", 1)[-1]
        if name in classes and meta.get("layer"):
            classes[name].layer_override = meta["layer"]
    return classes, edges
