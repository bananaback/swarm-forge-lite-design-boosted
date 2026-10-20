"""Resolve the project from the pack config, so the tool never assumes a cwd."""

from __future__ import annotations

import json
from pathlib import Path

PACK = Path(__file__).resolve().parents[2]
_CONFIG = json.loads((PACK / "config" / "pack.json").read_text(encoding="utf-8"))
PROJECT = (PACK / _CONFIG["project_root"]).resolve()
APP = (PROJECT / _CONFIG["source_roots"][0]).resolve()
PIPELINE = APP / "pipeline"
DOCS = (PROJECT / _CONFIG.get("docs_root", "deepstream/docs")).resolve()
ARCHITECTURE = PACK / "architecture"
RUNTIME = ARCHITECTURE / "runtime.json"
DESIGN = ARCHITECTURE / "design.json"
