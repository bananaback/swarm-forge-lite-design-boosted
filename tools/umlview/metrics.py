"""Attach crapper's CRAP metrics to the generated model."""

from __future__ import annotations

from pathlib import Path

from edn import loads
import json

from edn import loads
from model import CRAP_RED, Model, Node, Summary, crap_risk, summarize


def _entries(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    document = loads(path.read_text(encoding="utf-8"))
    entries = document.get("entries") if isinstance(document, dict) else None
    return list(entries or [])


def _module_of(namespace: str, package: str, prefix: str) -> tuple[str, str | None]:
    """Split ``...app.pipeline.a.b.ClassName`` into module id and class name."""
    marker = f".{package}."
    position = namespace.rfind(marker)
    if position < 0:
        return "", None
    relative = namespace[position + len(marker) :]
    parts = relative.split(".")
    class_name = parts[-1] if parts and parts[-1][:1].isupper() else None
    module_parts = parts[:-1] if class_name else parts
    module = ".".join([package, *module_parts])
    if prefix and module.startswith(prefix + "."):
        module = module[len(prefix) + 1 :]
    return module, class_name


def attach(model: Model, metrics_path: Path, package: str) -> int:
    """Fill op and node metrics in place. Returns the number of matched entries."""
    index = model.index()
    matched = 0
    for entry in _entries(metrics_path):
        namespace = str(entry.get("namespace", ""))
        name = str(entry.get("name", ""))
        module, class_name = _module_of(namespace, package, model.prefix)
        node = index.get(module)
        if node is None:
            continue
        qualified = f"{class_name}.{name}" if class_name else name
        coverage = entry.get("coverage")
        if coverage is not None and coverage > 1.0:
            coverage = coverage / 100.0
        for at, op in enumerate(node.ops):
            if op.name == qualified:
                node.ops[at] = type(op)(
                    name=qualified,
                    cc=entry.get("complexity"),
                    coverage=coverage,
                    crap=entry.get("crap"),
                )
                matched += 1
                break
    _roll_up(model)
    return matched


def _mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def _function_weight(node: Node) -> int:
    """Functions listed on a module, or one when it lists none."""
    return len(node.ops) if node.ops else 1


def _red(n: int) -> Summary:
    """No CRAP data: the red threshold, once per function."""
    return Summary(n=n, mu=CRAP_RED, sigma=0.0, max=CRAP_RED)


def _roll_up(model: Model) -> None:
    for node in model.nodes:
        scores = [op.crap for op in node.ops if op.crap is not None]
        node.cc = sum(op.cc for op in node.ops if op.cc is not None) or None
        node.coverage = _mean(
            [op.coverage for op in node.ops if op.coverage is not None]
        )
        node.summary = summarize(scores) or _red(_function_weight(node))
        node.crap = crap_risk(node.summary)


def attach_mutation(model: Model, mutate_dir: Path, package: str) -> int:
    """Join ``.metrics/mutate`` snapshots by namespace, as the overlay does."""
    if not mutate_dir.is_dir():
        model.mutation_present = False
        return 0
    files = sorted(mutate_dir.glob("*.edn")) + sorted(mutate_dir.glob("*.json"))
    if not files:
        model.mutation_present = False
        return 0
    index = model.index()
    seen: set[str] = set()
    for path in files:
        try:
            text = path.read_text(encoding="utf-8")
            document = json.loads(text) if path.suffix == ".json" else loads(text)
        except (OSError, ValueError):
            continue
        if not isinstance(document, dict):
            continue
        namespace = str(document.get("namespace", ""))
        module, _ = _module_of(namespace, package, model.prefix)
        node = index.get(module)
        if node is None:
            continue
        seen.add(module)
        forms = {
            str(form.get("id", "")).split("/", 1)[-1]: form
            for form in document.get("forms") or []
            if isinstance(form, dict)
        }
        scored = 0
        for op in node.ops:
            form = forms.get(op.name) or forms.get(op.name.split(".")[-1])
            if form is None:
                continue
            scored += 1
            node.killed += int(form.get("killed") or 0)
            node.survived += int(form.get("survived") or 0)
            node.uncovered = (node.uncovered or 0) + int(form.get("uncovered") or 0)
            node.sites += int(form.get("sites") or 0)
        node.mut_gap += max(len(node.ops) - scored, 0)
    for node in model.nodes:
        if node.id not in seen:
            node.mut_gap = max(len(node.ops), 1)
    model.mutation_present = bool(seen)
    return len(seen)
