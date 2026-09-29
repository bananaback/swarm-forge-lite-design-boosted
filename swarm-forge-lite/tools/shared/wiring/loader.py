"""Load a config file into the resolved path set."""

import os
import re
from pathlib import Path

from .config import ConfigFile
from .errors import WiringError
from .locator import ConfigLocator, PackConfigLocator
from .pack import Pack, resolve_pack_root
from .resolver import PathResolver
from .wiring import Wiring

LANE_ENV = "SWARM_LANE"
_LANE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*\Z")


def lane_from(environ=None) -> str:
    """The lane selector: ``SWARM_LANE`` as one safe path segment, or empty."""
    environ = os.environ if environ is None else environ
    lane = (environ.get(LANE_ENV) or "").strip()
    if lane and not _LANE.match(lane):
        raise WiringError(f"{LANE_ENV} must be one path segment, got {lane!r}")
    return lane


class HarnessConfig:
    """Interpret a ConfigFile into resolved Wiring, scoped to an optional lane."""

    def __init__(self, file: ConfigFile, pack: Pack, lane: str = ""):
        self._file = file
        self._pack = pack
        self._lane = lane
        self._paths = PathResolver(file.directory)

    def _scoped(self, base: Path) -> Path:
        """A disposable root, nested under the lane when one is selected."""
        return base / self._lane if self._lane else base

    def wiring(self) -> Wiring:
        root = self._paths.path
        features = self._file.value("features")
        specs = self._file.value("specs")
        return Wiring(
            pack_root=self._pack.root,
            workspace_root=root(self._file.value("workspace_root", "..")),
            state_root=self._scoped(root(self._file.value("state_root", ".swarmforge"))),
            artifacts_root=self._scoped(root(self._file.value("artifacts_root", "dump"))),
            hot_tests=self._scoped(root(self._file.value("hot_tests", "hot_tests"))),
            persistent_tests=self._paths.persistent_tests(
                self._file.entries("persistent_tests")
            ),
            source_roots=self._paths.paths(
                self._file.value("source_roots", ["src"])
            ),
            features=self._paths.optional_path(features),
            specs=self._paths.optional_path(specs),
            config_path=self._file.path,
        )


def load(config=None, locator: ConfigLocator | None = None, environ=None) -> Wiring:
    """Resolve every path a tool needs from the selected config and lane."""
    pack = Pack(resolve_pack_root(environ))
    source = locator or PackConfigLocator(pack, config, environ)
    file = ConfigFile(source.locate())
    return HarnessConfig(file, pack, lane_from(environ)).wiring()
