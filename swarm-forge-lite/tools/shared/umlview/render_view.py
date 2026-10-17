from __future__ import annotations

import argparse
import html
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from render_grade import stamp_grades
from render_model import apply_policy, level_ranks, rank_of

DEFAULT_TEMPLATE = HERE / "template.html"
DEFAULT_DAGRE = HERE / "vendor" / "dagre.min.js"


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