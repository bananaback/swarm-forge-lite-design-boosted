#!/usr/bin/env python3
"""umlview render -- UML model -> one standalone HTML diagram.

The model and every rule below are a faithful port of unclebob/uml-viewer's domain
(`domain/ir.clj` normalization, `domain/policy.clj` ranks + dependency rule,
`domain/config.clj` crap grades). We changed three things: the display is HTML/SVG
instead of Quil, the language analysis (`scan_python.py`) reads Python instead of
Clojure, and a module with no functions is not graded (`_crap_sample`). No new concepts.

Upstream-only findings:
  - `dep-rule`   : a :dependency from an inner to an outer rank (policy.clj)
  - `dup-id`     : duplicate class id               (ir.clj throws)
  - `bad-edge`   : edge naming an unknown class      (ir.clj throws)

Upstream-only grades (config.clj): `crap-risk` (mu + sigma), `crap-grade` (the risk on
the 1-10 scale over the stops 8/12/20), and `pool-crap` (function-weighted mu, max and
population sigma). The mutation half of the upstream model is not ported.

Usage:
  render.py MODEL.json [--out OUT.html] [--template PATH] [--dagre PATH] [--check] [--public]
"""

from __future__ import annotations

import argparse
import html
import json
import math
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_TEMPLATE = HERE / "template.html"
DEFAULT_DAGRE = HERE / "vendor" / "dagre.min.js"

# --------------------------------------------------------------------------- #
# upstream concepts (uml-viewer/domain/policy.clj)
# --------------------------------------------------------------------------- #

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


# --- display projection (ours) ------------------------------------------------ #


def display_components(doc: dict) -> list:
    """The flat clusters we draw: upstream packages, plus foreign ovals if any."""
    components = [
        {"id": p["id"], "label": p["label"], "classes": p["classes"]}
        for p in doc["packages"]
    ]
    foreign = [c for c in doc["foreign"] if c.get("shape") == "oval"]
    if foreign:
        components.append({"id": "external", "label": "External", "classes": foreign})
    return components


def findings(doc: dict, errors: list) -> list:
    out = list(errors)
    for e in doc.get("edges", []):
        if e.get("violating"):
            rf = rank_of(e["from"], level_ranks(doc))
            rt = rank_of(e["to"], level_ranks(doc))
            out.append(
                {
                    "sev": "error",
                    "code": "dep-rule",
                    "msg": f"{e['from']} -> {e['to']} points inner (rank {rf}) -> outer (rank {rt})",
                    "ids": [e["from"], e["to"]],
                }
            )
    order = {"error": 0, "warn": 1, "info": 2}
    out.sort(key=lambda d: (order[d["sev"]], d["code"]))
    return out


# --------------------------------------------------------------------------- #
# grade logic (uml-viewer/domain/config.clj)
# --------------------------------------------------------------------------- #

CRAP_THRESHOLDS = {"green": 8, "yellow": 12, "red": 20}
GRADE_BEST = 10.0
GRADE_MID = 5.5
GRADE_WORST = 1.0


def crap_band(score):
    """config.clj `crap-band`: the traffic light for a CRAP score. Missing is red."""
    if score is None:
        return "red"
    if score <= CRAP_THRESHOLDS["green"]:
        return "green"
    if score <= CRAP_THRESHOLDS["yellow"]:
        return "yellow"
    return "red"


def _lerp(x, x0, x1, y0, y1):
    """config.clj `lerp`: linear interpolation between two stops."""
    if float(x0) == float(x1):
        return float(y0)
    t = (float(x) - float(x0)) / (float(x1) - float(x0))
    return y0 + t * (y1 - y0)


def _along(x, x0, x1, x2, y0, y1, y2):
    """config.clj `along`: clamp x onto the stops [x0 x1 x2] mapped to [y0 y1 y2]."""
    x = float(x)
    if x <= x0:
        return y0
    if x <= x1:
        return _lerp(x, x0, x1, y0, y1)
    if x <= x2:
        return _lerp(x, x1, x2, y1, y2)
    return y2


def crap_risk(crap):
    """config.clj `crap-risk`: mu + sigma of a pooled CRAP map, or None."""
    if not crap or crap.get("mu") is None:
        return None
    return float(crap["mu"]) + float(crap.get("sigma") or 0)


def crap_grade(score):
    """config.clj `crap-grade`: the CRAP risk on the 1-10 scale, 10 is best.
    Missing counts as red (1)."""
    if score is None:
        return GRADE_WORST
    return _along(
        score,
        CRAP_THRESHOLDS["green"],
        CRAP_THRESHOLDS["yellow"],
        CRAP_THRESHOLDS["red"],
        GRADE_BEST,
        GRADE_MID,
        GRADE_WORST,
    )


def combined_grade(*grades):
    """config.clj `combined-grade`, with the mutation half dropped: the mean of
    the present grades. None when no grade is present."""
    present = [g for g in grades if g is not None]
    if not present:
        return None
    return sum(present) / len(present)


def _round1(x):
    """config.clj `round1`: the nearest tenth."""
    return float(math.floor(float(x) * 10 + 0.5) / 10)


def score_of(crap):
    """config.clj `score-of`: a CRAP number, or the mu of a CRAP map."""
    if isinstance(crap, bool):
        return None
    if isinstance(crap, (int, float)):
        return float(crap)
    if isinstance(crap, dict) and crap.get("mu") is not None:
        return float(crap["mu"])
    return None


def op_scores(module):
    """config.clj `op-scores`: the function CRAP scores of one module.
    The live overlay writes `op.metrics.crap`; a function without it drops."""
    scores = []
    for op in module.get("ops", []):
        score = score_of((op.get("metrics") or {}).get("crap"))
        if score is not None:
            scores.append(score)
    return scores


def function_weight(module):
    """config.clj `function-weight`: the functions listed, or one when none is.
    The fallback of one answers a rolled summary that covers a subtree with no
    listed functions. A module with no functions is not in that path: it has
    nothing to measure, so `_crap_sample` drops it."""
    count = len(module.get("ops", []))
    return count if count > 0 else 1


def _score_group(scores):
    """config.clj `score-group`: mu, max and population sigma of a score sample."""
    xs = [float(s) for s in scores]
    n = len(xs)
    mu = sum(xs) / n
    var = sum((s - mu) ** 2 for s in xs) / n
    return {"n": n, "mu": mu, "sigma": math.sqrt(var), "max": max(xs)}


def _round_group(group):
    return {
        "mu": _round1(group["mu"]),
        "max": _round1(group["max"]),
        "sigma": _round1(group["sigma"]),
        "n": int(group["n"]),
    }


def _red_group(n):
    """config.clj `red-group`: a module with no CRAP data, at the red threshold."""
    red = float(CRAP_THRESHOLDS["red"])
    return {"n": n, "mu": red, "sigma": 0.0, "max": red}


def _summary_weight(module, summary, scores):
    n = summary.get("n")
    if n and n > 0:
        return int(n)
    if scores:
        return len(scores)
    return function_weight(module)


def _known_group(n, summary):
    return {
        "n": n,
        "mu": float(summary["mu"]),
        "sigma": float(summary.get("sigma") or 0),
        "max": float(summary.get("max", summary["mu"])),
    }


def _crap_sample(module, rolled):
    """config.clj `crap-sample`: one module as an unrounded CRAP group.
    The function scores are the sample. With `rolled`, a summary that already
    covers the subtree wins over the module's own ops. A module that has
    functions but no CRAP data is the red threshold, once per function. A module
    with no functions has nothing to measure, so it contributes no group:
    upstream weights it as one function, and that grades an enum red."""
    scores = op_scores(module)
    summary = module.get("crap")
    has_summary = isinstance(summary, dict) and summary.get("mu") is not None
    if rolled and has_summary:
        return _known_group(_summary_weight(module, summary, scores), summary)
    if scores:
        return _score_group(scores)
    if has_summary:
        return _known_group(_summary_weight(module, summary, scores), summary)
    if not module.get("ops"):
        return None
    return _red_group(function_weight(module))


def is_module(module):
    """config.clj `module?`: a real module, not a foreign oval."""
    return not (module.get("foreign") or module.get("shape") == "oval")


def _combine_groups(groups):
    """config.clj `combine-groups`: the function-weighted mu, sigma and max."""
    groups = [g for g in groups if g and g.get("n", 0) > 0]
    if not groups:
        return None
    n = sum(g["n"] for g in groups)
    sum_w = sum(g["n"] * g["mu"] for g in groups)
    sum_m2 = sum(g["n"] * (g["sigma"] ** 2 + g["mu"] ** 2) for g in groups)
    mx = max(g["max"] for g in groups)
    mu = sum_w / n
    var = max(0.0, sum_m2 / n - mu * mu)
    return _round_group({"n": n, "mu": mu, "sigma": math.sqrt(var), "max": mx})


def pool_crap(modules, rolled=False):
    """config.clj `pool-crap`: function-weighted mu, max and population sigma across
    modules. Each function weighs one. A module that has functions but no CRAP counts
    as the red threshold once per function; a module with no functions contributes
    nothing, because it has nothing to measure. `rolled` is true when each module's
    `crap` summary already pools its subtree."""
    return _combine_groups([_crap_sample(m, rolled) for m in modules if is_module(m)])


def grade_of(summary):
    """The 1-10 CRAP grade of a pooled summary, or None when nothing is pooled."""
    if summary is None:
        return None
    return crap_grade(crap_risk(summary))


def stamp_grades(components):
    """Write the pooled CRAP summary and its grade onto every component and class.
    The pool is rolled: a component trusts the summary of each class. Every op
    carries the band of its own CRAP, so the template never computes a threshold.
    A module with no pool - a class with nothing to measure - carries no risk,
    grade or band, and the template draws no grade for it."""
    for component in components:
        for cls in component["classes"]:
            cls["crap"] = pool_crap([cls])
            for op in cls.get("ops", []):
                crap = score_of((op.get("metrics") or {}).get("crap"))
                if crap is not None:
                    op["band"] = crap_band(crap)
        component["crap"] = pool_crap(component["classes"], rolled=True)
        for module in [component, *component["classes"]]:
            summary = module["crap"]
            if summary is None:
                module["risk"] = None
                continue
            risk = crap_risk(summary)
            module["risk"] = risk
            module["grade"] = combined_grade(crap_grade(risk))
            module["band"] = crap_band(risk)


# --------------------------------------------------------------------------- #
# page
# --------------------------------------------------------------------------- #


def render(
    model_path: Path,
    out_path: Path,
    template_path: Path,
    dagre_path: Path,
    public: bool = False,
) -> int:
    raw = json.loads(model_path.read_text())
    doc, errors = apply_policy(raw)
    diags = findings(doc, errors)
    components = display_components(doc)
    stamp_grades(components)
    model = {
        "title": doc["title"],
        "direction": doc["direction"],
        "components": components,
        "edges": doc["edges"],
        "levels": doc["levels"],
        "live": raw.get("live"),
    }
    if public:
        # the archive must not reveal how it was made: drop the LIVE badge, the
        # source-sync status, and any pack path. Metrics, code and signatures stay.
        model.pop("live", None)
        for component in model["components"]:
            for cls in component["classes"]:
                cls.pop("live", None)
                for op in cls.get("ops", []):
                    op.pop("live", None)

    template = template_path.read_text()
    dagre = dagre_path.read_text() if dagre_path.exists() else ""
    counts = {
        s: sum(1 for d in diags if d["sev"] == s) for s in ("error", "warn", "info")
    }
    page = (
        template.replace("__DAGRE__", dagre)
        .replace("__TITLE__", html.escape(str(model["title"]), quote=True))
        .replace("__MODEL_JSON__", json.dumps(model).replace("</", "<\\/"))
        .replace("__FINDINGS_JSON__", json.dumps(diags).replace("</", "<\\/"))
    )
    if public:
        # the archive must not name the tool that made it: drop the viewer's JS
        # global so a repo reader cannot tell the design was rendered by a tool.
        page = re.sub(r"window\.umlview = \{ [^\n]*\};\n?", "", page)
    out_path.write_text(page)
    print(
        f"wrote {out_path}  ({counts['error']} violations/errors, {counts['warn']} warnings)"
    )
    for d in diags:
        if d["sev"] == "error":
            print(f"  ERROR {d['code']}: {d['msg']}")
    return 1 if counts["error"] else 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="umlview-render")
    parser.add_argument("model")
    parser.add_argument("--out")
    parser.add_argument("--template", default=str(DEFAULT_TEMPLATE))
    parser.add_argument("--dagre", default=str(DEFAULT_DAGRE))
    parser.add_argument("--check", action="store_true")
    parser.add_argument(
        "--public",
        action="store_true",
        help="strip process metadata (LIVE badge, source status, pack paths)",
    )
    args = parser.parse_args(argv)
    model_path = Path(args.model)
    if not model_path.exists():
        print(f"render: no such model: {model_path}", file=sys.stderr)
        return 2
    out_path = Path(args.out) if args.out else model_path.with_suffix(".html")
    code = render(
        model_path, out_path, Path(args.template), Path(args.dagre), args.public
    )
    return code if args.check else 0


if __name__ == "__main__":
    sys.exit(main())
