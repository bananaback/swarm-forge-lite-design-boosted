"""Locate the harness pack from a persistent root that may sit anywhere.

A project-side persistent root can live inside the pack or anywhere in the
project tree, so its own depth says nothing about where the pack is. The pack is
found by `SWARM_PACK` first - the lane wrapper exports it - then by a walk up the
tree for the pack's `tools/shared/wiring`. A root that sits outside the pack and
runs without the lane wrapper must set `SWARM_PACK`.
"""

import os
from pathlib import Path

MARKER = Path("tools") / "shared" / "wiring"
PACK_DIR = "swarm-forge-lite"


def tools_shared() -> Path:
    """The pack's `tools/shared`, or raise with the fix."""
    chosen = os.environ.get("SWARM_PACK")
    if chosen:
        return Path(chosen).expanduser().resolve() / "tools" / "shared"
    for parent in Path(__file__).resolve().parents:
        if (parent / MARKER).is_dir():
            return parent / "tools" / "shared"
        if (parent / PACK_DIR / MARKER).is_dir():
            return parent / PACK_DIR / "tools" / "shared"
    raise RuntimeError(
        "cannot locate the harness pack: set SWARM_PACK=<pack root>, "
        "or run the command through the lane wrapper."
    )
