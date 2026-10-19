from __future__ import annotations

import re

KIND_RANK = {
    "implements": 4,
    "inheritance": 4,
    "composition": 3,
    "aggregation": 2,
    "association": 1,
    "dependency": 0,
}
DEFAULT_KIND = "association"
DISPLAY_ONLY = ("core", "secret", "responsibility")  # our annotations; never a finding


def as_id(value) -> str:
    """policy.clj `as-id`: a string is lower-cased with runs of space -> '-'."""
    if isinstance(value, str):
        return re.sub(r"\s+", "-", value).lower()
    return str(value)


def _member_text(m: dict) -> str:
    name = m.get("name", "")
    args = m.get("args") or []
    arg_text = ", ".join(a if isinstance(a, str) else a.get("name", "") for a in args)
    text = f"{name}({arg_text})" if args else str(name)
    if m.get("type"):
        text += f" : {m['type']}"
    if m.get("returns"):
        text += f" : {m['returns']}"
    return text


def as_member(m: dict) -> dict:
    if isinstance(m, str):
        return {"text": m}
    out = {"text": m.get("text") or _member_text(m)}
    if m.get("private"):
        out["private"] = True
    for key in ("name", "args", "returns", "type", "code"):
        if key in m:
            out[key] = m[key]
    annotations = dict(m.get("annotations") or {})
    for key in ("cqs", "pre", "post", "invariant", "visibility"):
        if key in m:
            annotations.setdefault(key, m[key])
    if annotations:
        out["annotations"] = annotations
    if isinstance(m.get("metrics"), dict):
        out["metrics"] = m["metrics"]
    if isinstance(m.get("live"), dict):
        out["live"] = m["live"]
    return out


def as_class(c: dict) -> dict:
    name = c.get("name") or as_id(c.get("id", ""))
    annotations = dict(c.get("annotations") or {})
    for extra in DISPLAY_ONLY:
        if extra in c:
            annotations.setdefault(extra, c[extra])
    out = {
        "id": as_id(c.get("id") or name),
        "name": name,
        "stereotype": c.get("stereotype"),
        "hide_members": bool(c.get("hide_members")),
        "fields": [as_member(f) for f in c.get("fields", [])],
        "ops": [as_member(o) for o in c.get("ops", [])],
    }
    if c.get("ns"):
        out["ns"] = str(c["ns"])
    if c.get("level") is not None:
        out["level"] = int(c["level"])
    if c.get("foreign") or c.get("shape") == "oval":
        out["shape"] = "oval"
    if annotations:
        out["annotations"] = annotations
    if isinstance(c.get("live"), dict):
        out["live"] = c["live"]
    return out


def as_package(p: dict) -> dict:
    label = p.get("label") or as_id(p.get("id", ""))
    return {
        "id": as_id(p.get("id") or label),
        "label": label,
        "classes": [as_class(c) for c in p.get("classes", [])],
    }


def as_edge(e: dict) -> dict:
    out = {
        "from": as_id(e["from"]),
        "to": as_id(e["to"]),
        "kind": str(e.get("kind") or DEFAULT_KIND),
    }
    if e.get("label"):
        out["label"] = e["label"]
    if e.get("violating") is True:
        out["violating"] = True
    return out


def normalize(raw: dict) -> tuple:
    """ir.clj `normalize`: build the document, then validate. Errors are findings here."""
    components = raw.get("packages", raw.get("components"))
    if components is None and raw.get("classes"):
        # hierarchical form: flat classes grouped by their top dotted segment (top-seg)
        groups = {}
        for c in raw["classes"]:
            seg = str(as_id(c.get("id") or c.get("name", ""))).split(".")[0]
            groups.setdefault(seg, []).append(c)
        order = [as_id(s) for s in (raw.get("order") or [])]
        rank = {seg: i for i, seg in enumerate(order)}
        components = [
            {"id": seg, "label": seg, "classes": cs}
            for seg, cs in sorted(groups.items(), key=lambda kv: rank.get(kv[0], 999))
        ]
    doc = {
        "title": raw.get("title") or "UML",
        "direction": raw.get("direction") or "tb",
        "packages": [as_package(p) for p in (components or [])],
        "foreign": [
            as_class(dict(f, foreign=True))
            if not isinstance(f, str)
            else as_class({"id": f, "name": f, "foreign": True})
            for f in raw.get("foreign", [])
        ],
        "edges": [as_edge(e) for e in raw.get("edges", [])],
        "levels": raw.get("levels") or [],
        "edge_kinds": raw.get("edge-kinds", raw.get("edge_kinds", {})) or {},
        "omit_edges": raw.get("omit-edges", raw.get("omit_edges", [])) or [],
        "omit": raw.get("omit", []) or [],
        "prefix": raw.get("prefix"),
        "order": raw.get("order", []) or [],
    }
    errors = []
    ids = [c["id"] for p in doc["packages"] for c in p["classes"]] + [
        c["id"] for c in doc["foreign"]
    ]
    seen, dup = set(), set()
    for cid in ids:
        if cid in seen:
            dup.add(cid)
        seen.add(cid)
    for cid in sorted(dup):
        errors.append(
            {
                "sev": "error",
                "code": "dup-id",
                "msg": f"duplicate class id {cid!r}",
                "ids": [cid],
            }
        )
    known = set(ids)
    for e in doc["edges"]:
        for side in ("from", "to"):
            if e[side] not in known:
                errors.append(
                    {
                        "sev": "error",
                        "code": "bad-edge",
                        "msg": f"edge {e['from']} -> {e['to']} names unknown class {e[side]!r}",
                        "ids": [e["from"], e["to"]],
                    }
                )
    return doc, errors


# --- ranks (policy.clj level-groups / level-ranks / rank-of) ------------------ #


def level_groups(doc: dict) -> list:
    return [list(group) for group in doc.get("levels", []) if group]


def level_ranks(doc: dict) -> dict:
    ranks = {}
    for rank, group in enumerate(level_groups(doc)):
        for segment in group:
            ranks[as_id(segment)] = rank
    return ranks


def rank_of(cid: str, ranks: dict):
    """policy.clj `rank-of`: exact key, else longest dotted prefix."""
    parts = str(cid).split(".")
    for n in range(len(parts), 0, -1):
        hit = ranks.get(".".join(parts[:n]))
        if hit is not None:
            return hit
    return None


def violating_dependency(edge: dict, ranks: dict) -> bool:
    """policy.clj `violating-dependency?`: only :dependency, both ranked, inner -> outer."""
    if edge.get("kind") != "dependency":
        return False
    rf, rt = rank_of(edge["from"], ranks), rank_of(edge["to"], ranks)
    return rf is not None and rt is not None and rf < rt


# --- edges (policy.clj merge-edges / mark-violations / apply-edge-kinds) ------- #


def merge_edges(edges: list) -> list:
    """per [from to] keep the strongest kind; violation survives iff that is a :dependency
    and any bundled edge was violating."""
    merged = {}
    for e in edges:
        key = (e["from"], e["to"])
        best = merged.get(key)
        if best is None or KIND_RANK.get(e["kind"], 0) > KIND_RANK.get(best["kind"], 0):
            merged[key] = dict(e)
        if e.get("violating"):
            merged[key].setdefault("_any_violating", True)
    out = []
    for e in merged.values():
        e = dict(e)
        any_viol = e.pop("_any_violating", False)
        if e.get("kind") == "dependency" and any_viol:
            e["violating"] = True
        out.append(e)
    return out


def mark_violations(edges: list, ranks: dict) -> list:
    out = []
    for e in edges:
        e = dict(e)
        if ranks and violating_dependency(e, ranks):
            e["violating"] = True
        else:
            e.pop("violating", None)  # policy.clj dissoc when not violating
        out.append(e)
    return out


def apply_edge_kinds(edges: list, kinds: dict, omit: list) -> list:
    omit_pairs = {
        (as_id(p[0]), as_id(p[1]))
        for p in omit
        if isinstance(p, (list, tuple)) and len(p) == 2
    }
    out = []
    for e in edges:
        if (e["from"], e["to"]) in omit_pairs:
            continue
        override = kinds.get(f"{e['from']}->{e['to']}")
        if override:
            e["kind"] = str(override)
        if e["kind"] != "dependency":
            e.pop("violating", None)
        out.append(e)
    return out


def collapse_graph(doc: dict) -> list:
    """policy.clj `collapse-graph`: remap foreign ids to their listed prefix, drop
    self-edges, then merge. Foreign endpoints not matching a listed prefix drop."""
    prefixes = sorted(
        (c["id"] for c in doc["foreign"] if c.get("shape") == "oval"),
        key=len,
        reverse=True,
    )

    def remap(cid):
        for pre in prefixes:
            if cid == pre or str(cid).startswith(pre + "."):
                return pre
        return cid

    project = _project_ids(doc)
    kept = []
    for e in doc["edges"]:
        f, t = remap(e["from"]), remap(e["to"])
        if f == t:
            continue
        if f not in project and f not in prefixes:
            continue
        if t not in project and t not in prefixes:
            continue
        kept.append({**e, "from": f, "to": t})
    return merge_edges(kept)


def _project_ids(doc: dict) -> set:
    return {c["id"] for p in doc["packages"] for c in p["classes"]}


def with_levels(doc: dict, ranks: dict):
    for p in doc["packages"]:
        for c in p["classes"]:
            lv = rank_of(c["id"], ranks)
            if lv is not None and c.get("shape") != "oval":
                c["level"] = lv


def apply_policy(raw: dict) -> tuple:
    """policy.clj `apply-policy` for the flat view: collapse -> mark -> levels -> kinds."""
    doc, errors = normalize(raw)
    ranks = level_ranks(doc)
    doc["edges"] = collapse_graph(doc)
    doc["edges"] = mark_violations(doc["edges"], ranks)
    with_levels(doc, ranks)
    doc["edges"] = apply_edge_kinds(doc["edges"], doc["edge_kinds"], doc["omit_edges"])
    return doc, errors
