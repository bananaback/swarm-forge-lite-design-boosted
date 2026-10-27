#!/usr/bin/env python3
"""Render one UML class diagram per subsystem into a single page.

The model is extracted from the AST, so it cannot drift from the code:

- ``extends``      a class lists another class as a base
- ``implements``   a Protocol/ABC base, or a class carrying every method of a
                   protocol whose name it ends with (Python is structural)
- ``composition``  ``__init__`` constructs the collaborator itself
- ``aggregation``  ``__init__`` receives the collaborator as a parameter
- ``dependency``   any other reference to a class of the same subsystem

The page draws with Cytoscape + ELK (vendored), so the layout is a real layered
graph rather than a hand-packed grid. Output: ``<PROJECT>/<docs_root>/diagrams.html``.
"""

from __future__ import annotations

import argparse
import ast
import json
from dataclasses import dataclass, field
from pathlib import Path

DIAGRAMS = (
    ("01 · 02", "detector", ("detector",)),
    ("04", "safety_rule_engine", ("safety_rule_engine",)),
    ("05", "detection_extraction", ("detection_extraction",)),
    ("06", "rule_check_osd", ("rule_check_osd",)),
    ("07", "audio / alerts", ("audio/alert", "audio/catalog", "audio/gate")),
    ("08", "audio / output", ("audio/output", "audio/playback")),
    ("09", "message_publish", ("message_publish",)),
    ("10", "latency_monitoring", ("latency_monitoring",)),
    ("03", "privacy_record", ("privacy_record",)),
)

STEREOTYPES = {
    "interface": ("«interface»", "#e8f0fb", "#4a7bd0"),
    "abstract": ("«abstract»", "#f3ecfb", "#8b5cf6"),
    "enum": ("«enum»", "#fdf6e3", "#b78a2f"),
    "data": ("«data»", "#eef7ec", "#4f9d5d"),
    "exception": ("«exception»", "#fdecec", "#c05a5a"),
    "concrete": ("", "#ffffff", "#64748b"),
    "class": ("", "#ffffff", "#64748b"),
}

PROTOCOLS = {"Protocol"}
ABSTRACTS = {"ABC", "ABCMeta"}
ENUMS = {"Enum", "StrEnum", "IntEnum", "Flag", "IntFlag"}
EXCEPTIONS = {"Exception", "BaseException", "RuntimeError", "ValueError", "TypeError"}


@dataclass
class ClassInfo:
    name: str
    module: str
    group: str
    methods: list[str] = field(default_factory=list)
    bases: list[str] = field(default_factory=list)
    stereotype: str = "concrete"
    composed: list[str] = field(default_factory=list)
    aggregated: list[str] = field(default_factory=list)
    depended: list[str] = field(default_factory=list)
    note: str = ""
    layer_override: str | None = None

    @property
    def layer(self) -> str:
        if self.layer_override:
            return self.layer_override
        return "shell" if "shell" in self.module.split("/") else "core"


def _name(node: ast.AST | None) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
        return _name(node.left) or _name(node.right)
    if isinstance(node, ast.Subscript):
        return _name(node.value)
    if isinstance(node, ast.Call):
        return _name(node.func)
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value.split(".")[-1].split("|")[0].strip()
    return None


def _call(node: ast.AST | None) -> str | None:
    return _name(node.func) if isinstance(node, ast.Call) else None


def _decorators(node: ast.ClassDef) -> set[str]:
    return {name for name in (_name(d) for d in node.decorator_list) if name}


def _stereotype(node: ast.ClassDef, bases: list[str]) -> str:
    base_set = set(bases)
    if "dataclass" in _decorators(node):
        return "data"
    if base_set & ENUMS:
        return "enum"
    if base_set & EXCEPTIONS:
        return "exception"
    if base_set & PROTOCOLS:
        return "interface"
    if base_set & ABSTRACTS:
        return "abstract"
    for child in ast.walk(node):
        if isinstance(child, ast.FunctionDef) and any(
            _name(d) == "abstractmethod" for d in child.decorator_list
        ):
            return "abstract"
    return "concrete"


def _is_self_attr(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Attribute)
        and isinstance(node.value, ast.Name)
        and node.value.id == "self"
    )


def _init_of(node: ast.ClassDef) -> ast.FunctionDef | None:
    return next(
        (x for x in node.body if isinstance(x, ast.FunctionDef) and x.name == "__init__"),
        None,
    )


def _scan_relations(cls: ast.ClassDef, info: ClassInfo, known: set[str]) -> None:
    init = _init_of(cls)
    params: dict[str, str | None] = {}
    if init is not None:
        for arg in (*init.args.posonlyargs, *init.args.args, *init.args.kwonlyargs):
            params[arg.arg] = _name(arg.annotation)
        for node in ast.walk(init):
            targets: list[ast.AST] = []
            value: ast.AST | None = None
            if isinstance(node, ast.Assign):
                targets, value = list(node.targets), node.value
            elif isinstance(node, ast.AnnAssign):
                targets, value = [node.target], node.value
            if value is None:
                continue
            for target in targets:
                if not _is_self_attr(target):
                    continue
                if isinstance(value, ast.IfExp):
                    injected, built = _name(value.body), _call(value.orelse)
                    if injected in params and params[injected] in known:
                        info.aggregated.append(params[injected])
                    elif built in known:
                        info.composed.append(built)
                    continue
                built = _call(value)
                if built in known and built != info.name:
                    info.composed.append(built)
                    continue
                if isinstance(value, ast.Name) and value.id in params:
                    declared = params[value.id]
                    if declared in known and declared != info.name:
                        info.aggregated.append(declared)

    seen = set(info.bases) | set(info.composed) | set(info.aggregated) | {info.name}
    for node in ast.walk(cls):
        if isinstance(node, ast.Name) and node.id in known and node.id not in seen:
            if node.id not in info.depended:
                info.depended.append(node.id)


def _group_of(module: str, prefix: str) -> str:
    rest = module[len(prefix) :].lstrip("/") if prefix else module
    return rest.split("/")[0] if "/" in rest else "root"


def scan(
    root: Path, packages: tuple[str, ...], layer: str | None = None
) -> dict[str, ClassInfo]:
    trees: list[ast.AST] = []
    classes: dict[str, ClassInfo] = {}
    order: list[str] = []
    prefix = packages[0].split("/")[0] if packages else ""
    for package in packages:
        for path in sorted((root / package).rglob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            trees.append(tree)
            module = "/".join(
                p for p in path.relative_to(root).with_suffix("").parts if p != "__init__"
            )
            for node in tree.body:
                if not isinstance(node, ast.ClassDef):
                    continue
                info = ClassInfo(
                    name=node.name,
                    module=module,
                    group=_group_of(module, prefix),
                    methods=[
                        x.name
                        for x in node.body
                        if isinstance(x, ast.FunctionDef) and not x.name.startswith("_")
                    ],
                    bases=[b for b in (_name(x) for x in node.bases) if b],
                )
                info.stereotype = _stereotype(node, info.bases)
                if layer:
                    info.layer_override = layer
                classes[node.name] = info
                order.append(node.name)
    known = set(classes)
    for tree in trees:
        for node in tree.body:
            if isinstance(node, ast.ClassDef) and node.name in classes:
                _scan_relations(node, classes[node.name], known)
    for info in classes.values():
        info.bases = [b for b in info.bases if b in known]
        info.composed = sorted({b for b in info.composed if b in known and b != info.name})
        info.aggregated = sorted(
            {b for b in info.aggregated if b in known and b != info.name}
        )
        excluded = set(info.bases) | set(info.composed) | set(info.aggregated)
        info.depended = sorted(
            {b for b in info.depended if b in known and b != info.name and b not in excluded}
        )
    return {name: classes[name] for name in order}


def relations(classes: dict[str, ClassInfo]) -> list[tuple[str, str, str]]:
    found: dict[tuple[str, str], str] = {}
    for info in classes.values():
        for base in info.bases:
            kind = (
                "implements"
                if classes[base].stereotype in {"interface", "abstract"}
                else "extends"
            )
            found[(info.name, base)] = kind
        for part in info.composed:
            found[(info.name, part)] = "composition"
        for part in info.aggregated:
            found.setdefault((info.name, part), "aggregation")
        for other in info.depended:
            found.setdefault((info.name, other), "dependency")
    # Python protocols are structural: a class that carries every method of a
    # protocol implements it even when it does not list it as a base.
    for proto in classes.values():
        if proto.stereotype not in {"interface", "abstract"} or not proto.methods:
            continue
        wanted = set(proto.methods)
        for candidate in classes.values():
            if candidate.name == proto.name or candidate.stereotype in {"interface", "abstract"}:
                continue
            if (candidate.name, proto.name) in found:
                continue
            if wanted <= set(candidate.methods) and candidate.name.endswith(proto.name):
                found[(candidate.name, proto.name)] = "implements"
    return [(a, b, k) for (a, b), k in sorted(found.items())]


def _elements(classes: dict[str, ClassInfo], edges: list[tuple[str, str, str]]) -> list[dict]:
    elements: list[dict] = []
    for info in classes.values():
        stereo = "" if info.stereotype == "concrete" else STEREOTYPES[info.stereotype][0]
        methods = ", ".join(info.methods[:3]) + ("…" if len(info.methods) > 3 else "")
        label = "\n".join(x for x in (info.name, stereo, methods) if x)
        elements.append(
            {
                "data": {
                    "id": info.name,
                    "label": label,
                    "name": info.name,
                    "stereotype": info.stereotype,
                    "layer": info.layer,
                    "group": info.group,
                    "module": info.module,
                    "methods": ", ".join(info.methods) or "—",
                    "note": info.note,
                }
            }
        )
    for index, (src, dst, kind) in enumerate(edges):
        elements.append(
            {
                "data": {
                    "id": f"e{index}",
                    "source": src,
                    "target": dst,
                    "kind": kind,
                    "detail": {"extends": "extends", "implements": "implements",
                               "composition": "composition", "aggregation": "aggregation",
                               "dependency": "dependency"}[kind],
                }
            }
        )
    return elements


VENDOR = ("cytoscape.min.js", "elk.bundled.js", "cytoscape-elk.js")


def _vendor_scripts() -> str:
    folder = Path(__file__).resolve().parent / "vendor"
    blocks = []
    for name in VENDOR:
        text = (folder / name).read_text(encoding="utf-8")
        blocks.append(f"<script>{text.replace('</script>', '<\\/script>')}</script>")
    return "\n".join(blocks)


def merged(
    root: Path, data: dict | None = None, diagrams: tuple | None = None
) -> dict[str, tuple[str, dict[str, ClassInfo], list]]:
    """Per subsystem: number, classes and edges, with the design overlay folded in."""
    import overlay as overlay_module

    overlays = data if data is not None else {"nodes": [], "edges": [], "annotations": {}}
    result: dict[str, tuple[str, dict[str, ClassInfo], list]] = {}
    for entry in (DIAGRAMS if diagrams is None else diagrams):
        number, label, packages = entry[0], entry[1], entry[2]
        layer = entry[3] if len(entry) > 3 else None
        classes = scan(root, packages, layer)
        edges = relations(classes)
        prefix = packages[0].split("/")[0]
        if overlays["nodes"] or overlays["edges"] or overlays["annotations"]:
            overlay_module.merge(
                classes, edges, overlays, label,
                lambda node, name: ClassInfo(
                    name=name,
                    module=node.get("module") or node["id"].rsplit(".", 1)[0].replace(".", "/"),
                    group=_group_of(node.get("module") or "", prefix),
                    stereotype=node.get("stereotype", "class"),
                    note=node.get("note", ""),
                ),
            )
            for class_id, meta in overlays.get("annotations", {}).items():
                name = class_id.rsplit(".", 1)[-1]
                if name in classes and meta.get("note"):
                    classes[name].note = meta["note"]
        result[label] = (number, classes, edges)
    return result


def class_id(info: ClassInfo) -> str:
    return info.module.replace("/", ".") + "." + info.name


def all_classes(
    root: Path, data: dict | None = None, diagrams: tuple | None = None
) -> dict[str, tuple[str, ClassInfo]]:
    """Flatten the model: full class id -> (subsystem, ClassInfo)."""
    flat: dict[str, tuple[str, ClassInfo]] = {}
    for label, (_number, classes, _edges) in merged(root, data, diagrams).items():
        for info in classes.values():
            flat[class_id(info)] = (label, info)
    return flat


def render(
    root: Path,
    out: Path,
    data: dict | None = None,
    diagrams: tuple | None = None,
    project: str = "project",
) -> None:
    panels, buttons, datasets = [], [], []
    for index, (label, (number, classes, edges)) in enumerate(
        merged(root, data, diagrams).items()
    ):
        datasets.append(_elements(classes, edges))
        active = " active" if index == 0 else ""
        buttons.append(
            f'<button class="tab{active}" data-index="{index}">{number} · {label}</button>'
        )
        panels.append(
            f'<section class="panel{active}" id="panel-{index}">'
            f'<div class="cy" id="cy-{index}"></div></section>'
        )

    page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>{project} — class diagrams</title>
<style>
  :root {{ color-scheme: light; }}
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; padding: 20px 24px 32px; font: 14px/1.5 system-ui, -apple-system, "Segoe UI", sans-serif; color: #1e293b; background: #fff; }}
  h1 {{ font-size: 20px; margin: 0 0 2px; }}
  p.lede {{ margin: 0 0 14px; color: #475569; max-width: 1100px; }}
  nav {{ display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 8px; }}
  button.tab {{ border: 1px solid #cbd5e1; background: #fff; color: #475569; border-radius: 999px; padding: 5px 12px; font: inherit; font-size: 12.5px; cursor: pointer; }}
  button.tab.active {{ background: #1e293b; border-color: #1e293b; color: #fff; }}
  button.ctl {{ border: 1px solid #cbd5e1; background: #fff; color: #334155; border-radius: 6px; width: 30px; height: 26px; font: inherit; cursor: pointer; }}
  button.ctl.wide {{ width: auto; padding: 0 10px; }}
  .bar {{ display: flex; align-items: center; gap: 18px; margin: 4px 0 10px; color: #475569; font-size: 12.5px; }}
  .bar label {{ display: inline-flex; align-items: center; gap: 6px; }}
  .panel {{ display: none; }}
  .panel.active {{ display: block; }}
  .cy {{ width: 100%; height: calc(100vh - 300px); min-height: 420px; border: 1px solid #e2e8f0; border-radius: 10px; background: #fcfdff; }}
  #info {{ margin-top: 8px; font-size: 12.5px; color: #475569; min-height: 20px; }}
  #info b {{ color: #1e293b; }}
  .legend {{ display: flex; flex-wrap: wrap; gap: 14px 20px; margin-top: 10px; font-size: 12px; color: #475569; }}
  .legend span {{ display: inline-flex; align-items: center; gap: 6px; }}
  .dot {{ width: 11px; height: 11px; border-radius: 3px; border: 1.3px solid; display: inline-block; }}
  .stroke {{ width: 26px; height: 0; border-top: 2px solid #475569; display: inline-block; }}
  .stroke.dash {{ border-top: 2px dashed #4a7bd0; }}
  .stroke.dep {{ border-top: 2px dashed #94a3b8; }}
  code {{ font-size: 12px; background: #f1f5f9; padding: 1px 5px; border-radius: 4px; }}
  .zoom {{ margin-left: auto; color: #64748b; font-variant-numeric: tabular-nums; }}
  #fail {{ display: none; color: #b91c1c; }}
</style></head><body>
<h1>{project} — class diagrams</h1>
<p class="lede">One subsystem per tab. Boxes are real classes with their UML stereotype; arrows are real references. Click a box or an arrow for details. The note says why a subsystem is shaped this way.</p>
<nav>{''.join(buttons)}</nav>
<div class="bar">
  <label><input type="checkbox" id="deps"> show dependency edges</label>
  <button class="ctl" id="zin">+</button>
  <button class="ctl" id="zout">−</button>
  <button class="ctl" id="zfit">fit</button>
  <span>drag to pan · scroll to zoom · click a class to isolate it</span>
  <span id="zoom" class="zoom">100%</span>
</div>
{''.join(panels)}
<div id="info"></div>
<div class="legend">
  <span><i class="dot" style="background:#e8f0fb;border-color:#4a7bd0"></i>«interface»</span>
  <span><i class="dot" style="background:#f3ecfb;border-color:#8b5cf6"></i>«abstract»</span>
  <span><i class="dot" style="background:#eef7ec;border-color:#4f9d5d"></i>«data»</span>
  <span><i class="dot" style="background:#fdf6e3;border-color:#b78a2f"></i>«enum»</span>
  <span><i class="dot" style="background:#fdecec;border-color:#c05a5a"></i>«exception»</span>
  <span><i class="stroke"></i> extends / composition / aggregation</span>
  <span><i class="stroke dash"></i> implements</span>
  <span><i class="stroke dep"></i> dependency</span>
</div>
<p class="lede" style="margin-top:10px">ELK places dependencies above dependents; shell classes carry a dashed border. Regenerate with <code>arch render classes</code>.</p>
<p id="fail">The bundled graph renderer failed to start.</p>
{_vendor_scripts()}
<script>
const DATA = {json.dumps(datasets)};
const STYLE = [
  {{ selector: 'node', style: {{
      'shape': 'round-rectangle', 'width': 240, 'height': 92,
      'background-color': '#ffffff', 'border-color': '#64748b', 'border-width': 1.4,
      'label': 'data(label)', 'text-wrap': 'wrap', 'text-max-width': 220,
      'font-size': 13, 'text-valign': 'center', 'text-halign': 'center',
      'color': '#1e293b', 'text-outline-width': 0 }} }},
  {{ selector: 'node[stereotype = "interface"]', style: {{ 'background-color': '#e8f0fb', 'border-color': '#4a7bd0', 'border-width': 1.8 }} }},
  {{ selector: 'node[stereotype = "abstract"]', style: {{ 'background-color': '#f3ecfb', 'border-color': '#8b5cf6', 'border-width': 1.8 }} }},
  {{ selector: 'node[stereotype = "data"]', style: {{ 'background-color': '#eef7ec', 'border-color': '#4f9d5d' }} }},
  {{ selector: 'node[stereotype = "enum"]', style: {{ 'background-color': '#fdf6e3', 'border-color': '#b78a2f' }} }},
  {{ selector: 'node[stereotype = "exception"]', style: {{ 'background-color': '#fdecec', 'border-color': '#c05a5a' }} }},
  {{ selector: 'node[layer = "shell"]', style: {{ 'border-style': 'dashed', 'border-width': 1.8 }} }},
  {{ selector: 'edge', style: {{ 'width': 1.5, 'curve-style': 'bezier', 'line-color': '#475569',
      'target-arrow-shape': 'triangle', 'target-arrow-fill': 'hollow', 'target-arrow-color': '#475569',
      'arrow-scale': 1.6 }} }},
  {{ selector: 'edge[kind = "implements"]', style: {{ 'line-style': 'dashed', 'line-color': '#4a7bd0',
      'target-arrow-color': '#4a7bd0' }} }},
  {{ selector: 'edge[kind = "composition"]', style: {{ 'target-arrow-shape': 'none',
      'source-arrow-shape': 'diamond', 'source-arrow-fill': 'filled', 'source-arrow-color': '#475569' }} }},
  {{ selector: 'edge[kind = "aggregation"]', style: {{ 'target-arrow-shape': 'none',
      'source-arrow-shape': 'diamond', 'source-arrow-fill': 'hollow', 'source-arrow-color': '#475569' }} }},
  {{ selector: 'edge[kind = "dependency"]', style: {{ 'line-style': 'dashed', 'line-color': '#94a3b8',
      'target-arrow-shape': 'vee', 'target-arrow-color': '#94a3b8', 'opacity': 0.65 }} }},
  {{ selector: '.dimmed', style: {{ 'opacity': 0.08 }} }}
];
const LAYOUT = {{ name: 'elk', animate: false, elk: {{
  'elk.algorithm': 'layered', 'elk.direction': 'DOWN', 'elk.edgeRouting': 'ORTHOGONAL',
  'elk.layered.nodePlacement.strategy': 'NETWORK_SIMPLEX', 'elk.aspectRatio': '1.7',
  'elk.layered.spacing.nodeNodeBetweenLayers': '55', 'elk.spacing.nodeNode': '24',
  'elk.spacing.edgeNode': '18', 'elk.spacing.edgeEdge': '10' }} }};
if (typeof cytoscape === 'undefined') {{ document.getElementById('fail').style.display = 'block'; }}
else {{
  cytoscape.use(cytoscapeElk);
  const instances = {{}};
  window.__cys = instances;
  const panels = [...document.querySelectorAll('.panel')];
  const tabs = [...document.querySelectorAll('button.tab')];
  const info = document.getElementById('info');
  function build(index) {{
    if (instances[index]) return instances[index];
    const el = document.getElementById('cy-' + index);
    const cy = cytoscape({{ container: el, elements: DATA[index], style: STYLE, layout: {{ name: 'preset' }} }});
    function focus(elements) {{
      cy.elements().addClass('dimmed');
      elements.removeClass('dimmed');
    }}
    function clearFocus() {{ cy.elements().removeClass('dimmed'); }}
    cy.on('tap', 'node', ev => {{
      const d = ev.target.data();
      focus(ev.target.closedNeighborhood());
      info.innerHTML = `<b>${{d.name}}</b> · ${{d.stereotype}} · ${{d.module}}<br>methods: ${{d.methods}}`;
    }});
    cy.on('tap', 'edge', ev => {{
      const d = ev.target.data();
      focus(ev.target.connectedNodes().union(ev.target));
      info.innerHTML = `<b>${{d.source}}</b> → <b>${{d.target}}</b> · ${{d.detail}}`;
    }});
    cy.on('tap', ev => {{ if (ev.target === cy) {{ clearFocus(); info.innerHTML = ''; }} }});
    if (!document.getElementById('deps').checked) cy.edges('[kind="dependency"]').style('display', 'none');
    instances[index] = cy;
    // ELK lays out asynchronously; frame the view only once positions exist.
    cy.on('zoom', () => {{ const z = document.getElementById('zoom'); if (z) z.textContent = Math.round(cy.zoom() * 100) + '%'; }});
    cy.one('layoutstop', () => {{ frame(cy, el); cy.__framed = true; }});
    cy.layout(LAYOUT).run();
    return cy;
  }}
  let current = 0;
  function frame(cy, el) {{
    const bb = cy.elements().boundingBox();
    const fit = Math.min(el.clientWidth / (bb.w + 40), el.clientHeight / (bb.h + 40));
    cy.zoom(Math.min(1.15, fit));
    cy.center();
  }}
  function show(index) {{
    current = index;
    panels.forEach((p, i) => p.classList.toggle('active', i === index));
    tabs.forEach((t, i) => t.classList.toggle('active', i === index));
    const cy = build(index);
    cy.resize();
    if (cy.__framed) cy.resize();
  }}
  document.getElementById('zin').onclick = () => instances[current] && instances[current].zoom({{ level: instances[current].zoom() * 1.2, renderedPosition: {{ x: 400, y: 300 }} }});
  document.getElementById('zout').onclick = () => instances[current] && instances[current].zoom({{ level: instances[current].zoom() / 1.2, renderedPosition: {{ x: 400, y: 300 }} }});
  document.getElementById('zfit').onclick = () => {{ const cy = instances[current]; if (cy) {{ cy.fit(undefined, 20); }} }};
  tabs.forEach(t => t.addEventListener('click', () => show(Number(t.dataset.index))));
  document.getElementById('deps').addEventListener('change', ev => {{
    Object.values(instances).forEach(cy => cy.edges('[kind="dependency"]').style('display', ev.target.checked ? 'element' : 'none'));
  }});
  show(0);
}}
</script>
</body></html>
"""
    out.write_text(page, encoding="utf-8")
    print(f"wrote {out} ({len(page)} bytes, {len(diagrams or DIAGRAMS)} diagrams)")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(__import__("paths").PIPELINE), type=Path)
    parser.add_argument("--out", default=str(__import__("paths").DOCS / "diagrams.html"), type=Path)
    args = parser.parse_args()
    render(args.root.resolve(), args.out.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
