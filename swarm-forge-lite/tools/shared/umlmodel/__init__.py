"""umlmodel -- query and mutate a uml model.json through one small op catalog.

Run it as `python3 <pack>/tools/shared/umlmodel <op> ...`, or through the
`swarm.uml` Code Mode tool. `umlmodel list` prints every op.
"""

from . import policy, query, validate
from .errors import UmlModelError
from .model import dumps, load, write_atomic
from .ops import OPS, entry, op_names

__all__ = [
    "OPS",
    "UmlModelError",
    "dumps",
    "entry",
    "load",
    "op_names",
    "policy",
    "query",
    "validate",
    "write_atomic",
]
