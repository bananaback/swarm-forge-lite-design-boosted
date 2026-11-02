"""Rule 28 — every harness tool imports the standard library only.

The vendored analyzers are capability bundles and are excluded; their
third-party dependency is declared in `doctor`'s capability rows.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

import pytest

PACK = Path(__file__).resolve().parents[2]
TOOLS = sorted(
    [
        *(PACK / "tools").glob("*.py"),
        *(PACK / "tools" / "design").glob("*.py"),
        *(PACK / "tools" / "umlview").glob("*.py"),
        PACK / "tools" / "shared" / "packconfig.py",
        PACK / "tools" / "shared" / "packschema.py",
    ]
)
LOCAL = {path.stem for path in TOOLS} | {"paths", "class_model", "overlay", "runtime_view"}


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            names.add(node.module.split(".")[0])
    return names


@pytest.mark.parametrize("path", TOOLS, ids=lambda path: path.name)
def test_only_stdlib_and_local_imports(path):
    third_party = {
        name
        for name in _imports(path)
        if name not in sys.stdlib_module_names and name not in LOCAL
    }

    assert not third_party, f"{path.name} imports {sorted(third_party)}"
