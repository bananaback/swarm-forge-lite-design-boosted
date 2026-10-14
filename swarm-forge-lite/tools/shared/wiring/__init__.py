"""wiring -- resolve harness paths from a harness.json config.

One config, one pack, two targets: the pack's own harness.json points the tools
at either the project under work or the harness itself. Every path resolves
relative to the config's directory.

The four actions live in one module each:

1. Find the config:  ``locator``  (``ConfigLocator`` / ``PackConfigLocator``)
2. Read it:          ``config``   (``ConfigFile``, ``parse_config``)
3. Resolve paths:    ``resolver`` (``PathResolver``)
4. Hand them out:    ``loader``   (``HarnessConfig``, ``load``)
"""

from .config import ConfigFile, parse_config
from .errors import WiringError
from .loader import lane_from, load
from .locator import ConfigLocator, PackConfigLocator
from .pack import PACK_ROOT, Pack, resolve_pack_root
from .resolver import PathResolver
from .wiring import Wiring

__all__ = [
    "PACK_ROOT",
    "ConfigFile",
    "ConfigLocator",
    "Pack",
    "PackConfigLocator",
    "PathResolver",
    "Wiring",
    "WiringError",
    "lane_from",
    "load",
    "parse_config",
    "resolve_pack_root",
]
