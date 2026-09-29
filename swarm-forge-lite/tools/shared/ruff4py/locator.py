"""Adapter that finds the linter executable on PATH."""

import shutil
from pathlib import Path

from .errors import ToolUnavailable

RUFF = "ruff"


class PathToolLocator:
    """Finds an executable by name, raising when PATH does not hold it."""

    def __init__(self, name: str = RUFF, which=shutil.which):
        self._name = name
        self._which = which

    def locate(self) -> Path:
        found = self._which(self._name)
        if not found:
            raise ToolUnavailable(self._name + " is not installed or not on PATH")
        return Path(found)
