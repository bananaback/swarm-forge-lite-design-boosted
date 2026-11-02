"""Locate and load the pack config, once, for every tool in the pack.

Two rules live here, and nothing else does:

- a tool never invents a config path: ``SWARM_CONFIG`` wins, then
  ``config/pack.local.json``, then the tracked legacy ``config/pack.json``;
- a value may point at the pack with the ``<PACK>`` token, so no config spells
  the pack's directory name and a renamed clone still resolves.

Stdlib only: this module is imported before anything else in the pack.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

LOCAL_NAME = "pack.local.json"
LEGACY_NAME = "pack.json"
TOKEN = "<PACK>"
INSTALL_HINT = "run python3 tools/install.py, or copy config/pack.example.json"


class ConfigError(RuntimeError):
    """The config is missing, unreadable, or does not name a usable project."""


def config_path(pack: Path, override: str | None = None) -> Path:
    """Return the config file this run must use, in precedence order."""
    requested = (override or os.environ.get("SWARM_CONFIG", "")).strip()
    if requested:
        return Path(requested).expanduser().resolve()
    local = pack / "config" / LOCAL_NAME
    if local.is_file():
        return local
    legacy = pack / "config" / LEGACY_NAME
    if legacy.is_file():
        return legacy
    raise ConfigError(
        f"no pack config: expected {local} or {legacy} — {INSTALL_HINT}"
    )


def expand(value, pack: Path):
    """Replace ``<PACK>`` in every string, recursively, with the pack root."""
    if isinstance(value, str):
        return value.replace(TOKEN, str(pack))
    if isinstance(value, list):
        return [expand(item, pack) for item in value]
    if isinstance(value, dict):
        return {key: expand(item, pack) for key, item in value.items()}
    return value


def load(pack: Path, override: str | None = None) -> dict:
    """Read, validate the shape, and expand one config file."""
    path = config_path(pack, override)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise ConfigError(f"cannot read {path}: {error} — {INSTALL_HINT}") from error
    if not isinstance(data, dict):
        raise ConfigError(f"{path}: the top level must be an object")
    return expand(data, pack)


def select(data: dict) -> tuple[str, str]:
    """Return (project name, where the selection came from)."""
    selector = data.get("selector_env", "PACK_PROJECT")
    projects = data.get("projects") or {}
    known = ", ".join(sorted(projects)) or "<none configured>"
    requested = os.environ.get(selector, "").strip()
    if requested:
        if requested not in projects:
            raise ConfigError(
                f"unknown project {requested!r} in {selector}; known: {known}"
            )
        return requested, selector
    default = data.get("default_project")
    if not default:
        raise ConfigError(f"no project selected: set {selector} to one of {known}")
    if default not in projects:
        raise ConfigError(
            f"default_project {default!r} is not configured; known: {known}"
        )
    return default, "default_project"
