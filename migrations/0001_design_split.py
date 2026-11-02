"""Copy authored design data from the pack into each project (additive)."""

from __future__ import annotations

import importlib.util
from pathlib import Path


def _migrate(pack: Path):
    spec = importlib.util.spec_from_file_location("design_migrate", pack / "tools" / "migrate.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def is_needed(pack: Path, config: dict) -> bool:
    for entry in (config.get("projects") or {}).values():
        root = entry.get("design_root")
        if not root:
            continue
        project = (pack / entry["project_root"]).resolve()
        if not (project / root / "runtime.json").is_file():
            return True
    return False


def apply(pack: Path, config: dict) -> None:
    module = _migrate(pack)
    module.apply(pack, config, sorted(config.get("projects") or {}))
