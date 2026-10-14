"""Registered acceptance step handlers for the harness tools.

Each feature area exports a ``HANDLERS`` list of ``(pattern, handler)`` pairs;
``STEP_HANDLERS`` concatenates them in registration order.
"""

from . import common
from .crapper import HANDLERS as CRAPPER
from .dryer import HANDLERS as DRYER
from .harness_cli import HANDLERS as HARNESS_CLI
from .ruff4py import HANDLERS as RUFF4PY
from .umlmodel import HANDLERS as UMLMODEL

STEP_HANDLERS = [
    *common.HANDLERS,
    *CRAPPER,
    *DRYER,
    *RUFF4PY,
    *HARNESS_CLI,
    *UMLMODEL,
]
