import importlib
import sys
from pathlib import Path

_PERSIST = Path(__file__).resolve().parent
_ENTRIES = (_PERSIST.parents[1] / "tools" / "shared", _PERSIST / "acceptance")
for _entry in _ENTRIES:
    if str(_entry) not in sys.path:
        sys.path.insert(0, str(_entry))

wiring = importlib.import_module("wiring")

for _root in wiring.load().source_roots:
    _entry = str(_root.parent)
    if _entry not in sys.path:
        sys.path.insert(0, _entry)
