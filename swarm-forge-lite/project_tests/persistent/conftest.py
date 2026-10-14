import importlib
import sys
from pathlib import Path

_PERSIST = Path(__file__).resolve().parent
sys.path.insert(0, str(_PERSIST / "acceptance"))

_packroot = importlib.import_module("packroot")

for _entry in (_packroot.tools_shared(), _PERSIST / "acceptance"):
    if str(_entry) not in sys.path:
        sys.path.insert(0, str(_entry))

wiring = importlib.import_module("wiring")

for _root in wiring.load().source_roots:
    _entry = str(_root.parent)
    if _entry not in sys.path:
        sys.path.insert(0, _entry)
