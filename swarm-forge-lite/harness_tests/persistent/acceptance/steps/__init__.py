"""Registered acceptance step handlers for the harness tools.

Each feature area exports a ``HANDLERS`` list of ``(pattern, handler)`` pairs;
``STEP_HANDLERS`` concatenates them in registration order.
"""

from . import common
from .crap4py import HANDLERS as CRAP4PY
from .dry4py import HANDLERS as DRY4PY
from .harness_cli import HANDLERS as HARNESS_CLI
from .ruff4py import HANDLERS as RUFF4PY

STEP_HANDLERS = [
    *common.HANDLERS,
    *CRAP4PY,
    *DRY4PY,
    *RUFF4PY,
    *HARNESS_CLI,
]
