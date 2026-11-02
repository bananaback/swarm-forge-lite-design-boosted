"""Resolve one project from the pack config, so no tool assumes a cwd.

A pack serves many projects. ``PACK_PROJECT`` selects one; when it is unset the
config's ``default_project`` applies. Every path below is derived from that
selection, so no prompt, role or tool hardcodes a project layout.

The config itself is found by ``packconfig``: ``SWARM_CONFIG``, then
``config/pack.local.json``, then the tracked legacy ``config/pack.json``. Paths
may use the ``<PACK>`` token instead of spelling the pack's folder name.
"""

from __future__ import annotations

import sys
from pathlib import Path

PACK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PACK / "tools" / "shared"))

import packconfig  # noqa: E402

try:
    CONFIG = packconfig.load(PACK)
    CONFIG_PATH = packconfig.config_path(PACK)
    NAME, SOURCE = packconfig.select(CONFIG)
except packconfig.ConfigError as error:
    raise SystemExit(str(error)) from None

PROJECTS: dict = CONFIG.get("projects", {})
SELECTOR_ENV: str = CONFIG.get("selector_env", "PACK_PROJECT")
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

# Authored design data: the project owns it when `design_root` is set; otherwise
# the tracked legacy `architecture/<project>/` is read and flagged.
_DESIGN_ROOT = CFG.get("design_root")
if _DESIGN_ROOT:
    DESIGN_DIR = (PROJECT / _DESIGN_ROOT).resolve()
    RUNTIME = DESIGN_DIR / "runtime.json"
    DESIGN = DESIGN_DIR / "overlay.json"
    LEGACY_DESIGN = False
else:
    DESIGN_DIR = PACK / "architecture" / NAME
    RUNTIME = DESIGN_DIR / "runtime.json"
    DESIGN = DESIGN_DIR / "design.json"
    LEGACY_DESIGN = True

ARCHITECTURE = DESIGN_DIR

_POLICY = UMLVIEW.get("policy")
if _POLICY:
    POLICY = (PROJECT / _POLICY).resolve()
elif LEGACY_DESIGN:
    POLICY = (PROJECT / "umlview.json").resolve()
else:
    POLICY = DESIGN_DIR / "policy.json"
