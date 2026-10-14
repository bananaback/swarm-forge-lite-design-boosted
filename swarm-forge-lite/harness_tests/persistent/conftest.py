"""Make the harness tool packages importable for the persistent tests."""

import sys
from pathlib import Path

PACK_ROOT = Path(__file__).resolve().parents[2]

for relative in ("tools/shared", "tools/refactorer"):
    path = PACK_ROOT / relative
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


# These tests assert on resolved root paths, so they must not inherit a lane
# from whatever invoked them. Run the suite through `lane` or not; the answer
# is the same either way.
import os

import pytest


@pytest.fixture(autouse=True)
def _unlaned(monkeypatch):
    monkeypatch.delenv("SWARM_LANE", raising=False)
    os.environ.pop("SWARM_LANE", None)
