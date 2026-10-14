"""The pack and where its own config lives."""

import os
from dataclasses import dataclass
from pathlib import Path

CONFIG_NAME = "harness.json"
PACK_ROOT = Path(__file__).resolve().parents[3]
PACK_ENV = "SWARM_PACK"


def resolve_pack_root(environ=None) -> Path:
    """The pack root: `SWARM_PACK` when set, else the installed pack."""
    environ = os.environ if environ is None else environ
    chosen = environ.get(PACK_ENV)
    if chosen:
        return Path(chosen).expanduser().resolve()
    return PACK_ROOT


@dataclass(frozen=True)
class Pack:
    """The pack that owns the tools; knows where its own config lives."""

    root: Path

    def config_path(self) -> Path:
        return self.root / CONFIG_NAME
