"""The module-grade view has its own self-test; run it under pytest (rule I10)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

PACK = Path(__file__).resolve().parents[2]


def test_umlview_selftest_passes():
    result = subprocess.run(
        [sys.executable, str(PACK / "tools" / "umlview" / "selftest.py")],
        cwd=PACK, capture_output=True, text=True, check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
