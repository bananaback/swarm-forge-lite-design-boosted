"""Choose which config file to read."""

import os
from collections.abc import Mapping
from pathlib import Path
from typing import Protocol

from .pack import Pack


class ConfigLocator(Protocol):
    """Decide which config file to read."""

    def locate(self) -> Path: ...


class PackConfigLocator:
    """Use an explicit path, SWARM_CONFIG, or the pack's own harness.json."""

    def __init__(self, pack: Pack, override=None, environ: Mapping | None = None):
        self._pack = pack
        self._override = override
        self._environ = os.environ if environ is None else environ

    def locate(self) -> Path:
        chosen = self._override or self._environ.get("SWARM_CONFIG")
        if chosen:
            return Path(chosen).expanduser().resolve()
        return self._pack.config_path()
