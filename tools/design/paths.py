"""Resolve one project from the pack config, so no tool assumes a cwd.

A pack serves many projects. ``PACK_PROJECT`` selects one; when it is unset the
config's ``default_project`` applies. Every path below is derived from that
selection, so no prompt, role or tool hardcodes a project layout.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

PACK = Path(__file__).resolve().parents[2]
CONFIG = json.loads((PACK / "config" / "pack.json").read_text(encoding="utf-8"))
PROJECTS: dict = CONFIG.get("projects", {})
SELECTOR_ENV: str = CONFIG.get("selector_env", "PACK_PROJECT")


def _select() -> tuple[str, str]:
    """Return (project name, where the selection came from)."""
    known = ", ".join(sorted(PROJECTS)) or "<none configured>"
    requested = os.environ.get(SELECTOR_ENV, "").strip()
    if requested:
        if requested not in PROJECTS:
            raise SystemExit(
                f"unknown project {requested!r} in {SELECTOR_ENV}; known: {known}"
            )
        return requested, SELECTOR_ENV
    default = CONFIG.get("default_project")
    if not default:
        raise SystemExit(
            f"no project selected: set {SELECTOR_ENV} to one of {known}"
        )
    if default not in PROJECTS:
        raise SystemExit(
            f"default_project {default!r} is not configured; known: {known}"
        )
    return default, "default_project"


NAME, SOURCE = _select()
CFG: dict = PROJECTS[NAME]
THRESHOLDS: dict = CONFIG.get("thresholds", {})

PROJECT = (PACK / CFG["project_root"]).resolve()
APP = (PROJECT / CFG["source_roots"][0]).resolve()

_CLASS_ROOT = CFG.get("class_root")
PIPELINE = (PROJECT / _CLASS_ROOT).resolve() if _CLASS_ROOT else APP

DOCS = (PROJECT / CFG.get("docs_root", "docs")).resolve()
SPECS: dict = dict(CFG.get("specs", {}))
ARTIFACTS = (PROJECT / CFG.get("artifacts_root", "tmp")).resolve()
UMLVIEW: dict = CFG.get("umlview", {})

# (number, label, packages[, layer]) per subsystem; the class view renders one
# tab and one spec per entry, and the layer removes the "must be named shell"
# assumption from the scanner.
SUBSYSTEMS: tuple = tuple(
    (
        entry.get("number", ""),
        entry["label"],
        tuple(entry.get("packages", ())),
        entry.get("layer"),
    )
    for entry in CFG.get("subsystems", [])
)

ARCHITECTURE = PACK / "architecture" / NAME
RUNTIME = ARCHITECTURE / "runtime.json"
DESIGN = ARCHITECTURE / "design.json"
