import importlib
from pathlib import Path

STEP_HANDLERS = []
for _path in sorted(Path(__file__).parent.glob("*.py")):
    if _path.stem == "__init__":
        continue
    _module = importlib.import_module(f"{__name__}.{_path.stem}")
    STEP_HANDLERS.extend(getattr(_module, "HANDLERS", []))
