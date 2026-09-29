"""Line hits parsed from an LCOV file."""

import os
from pathlib import Path

from .errors import ToolError
from .function import Function


class Coverage:
    """LCOV line hits per file; owns the lookup for a function's range."""

    def __init__(self, hits: dict[str, dict[int, int]]):
        self._hits = hits

    @classmethod
    def empty(cls) -> "Coverage":
        return cls({})

    @classmethod
    def load(cls, path: Path) -> "Coverage":
        hits: dict[str, dict[int, int]] = {}
        current = None
        for line in path.read_text().splitlines():
            if line.startswith("SF:"):
                current = hits.setdefault(os.path.abspath(line[3:]), {})
            elif line.startswith("DA:"):
                if current is None:
                    raise ToolError("malformed LCOV: DA before SF")
                number, count = line[3:].split(",")[:2]
                current[int(number)] = int(count)
        return cls(hits)

    def hits_for(self, function: Function) -> dict[int, int]:
        return self._hits.get(os.path.abspath(function.path), {})
