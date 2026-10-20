"""Render the generated model as one self-contained HTML page.

No server, no framework, no network. The model is embedded as JSON and the
viewer is vanilla SVG driven by a few hundred lines of JavaScript.
"""

from __future__ import annotations

import json
from pathlib import Path

from model import Document, Model, crap_grade, combined_grade, mutation_grade, mutation_ratio

TEMPLATE = Path(__file__).resolve().parent / "viewer.html"


def payload(model: Model, proposals: list | None = None) -> dict:
    return {
        "title": model.title,
        "prefix": model.prefix,
        "order": model.order,
        "levels": model.levels,
        "proposals": proposals or [],
        "foreign": model.foreign,
        "mode": model.mode,
        "mutation_present": model.mutation_present,
        "packages": [package.as_json() for package in model.packages],
        "foreign_classes": [node.as_json() for node in model.foreign_classes],
        "nodes": [
            {
                "id": node.id,
                "ns": node.ns,
                "name": node.name,
                "cc": node.cc,
                "coverage": node.coverage,
                "crap": node.crap,
                "grade": combined_grade(crap_grade(node.crap), mutation_grade(mutation_ratio(node)))
                if model.mutation_present
                else crap_grade(node.crap),
                "summary": node.summary.as_json() if node.summary else None,
                "killed": node.killed,
                "survived": node.survived,
                "gap": node.mut_gap,
                "fields": list(node.fields),
                "ops": [
                    {
                        "name": op.name,
                        "cc": op.cc,
                        "coverage": op.coverage,
                        "crap": op.crap,
                    }
                    for op in node.ops
                ],
            }
            for node in model.nodes
        ],
        "edges": [
            {
                "from": edge.src,
                "to": edge.dst,
                "kind": edge.kind,
                "violating": edge.violating,
            }
            for edge in model.edges
        ],
    }


def document_payload(document: Document, proposals: list | None = None) -> dict:
    return {
        "title": document.title,
        "diagrams": [
            payload(diagram, proposals if at == 0 else [])
            for at, diagram in enumerate(document.diagrams)
        ],
    }


def render(document: Document, target: Path, proposals: list | None = None) -> Path:
    template = TEMPLATE.read_text(encoding="utf-8")
    data = json.dumps(document_payload(document, proposals), separators=(",", ":"))
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(template.replace("/*__MODEL__*/", data), encoding="utf-8")
    return target
