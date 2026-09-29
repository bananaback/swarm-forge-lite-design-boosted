"""Make the harness tool packages importable for the persistent tests."""

import sys
from pathlib import Path

PACK_ROOT = Path(__file__).resolve().parents[2]

for relative in ("tools/shared", "tools/refactorer"):
    path = PACK_ROOT / relative
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))
