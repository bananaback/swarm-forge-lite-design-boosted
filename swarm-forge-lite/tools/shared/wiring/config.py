"""Read and validate a config document."""

import json
from pathlib import Path

from .errors import WiringError


def parse_config(path: Path) -> dict:
    """Read and validate a config document."""
    try:
        data = json.loads(path.read_text())
    except OSError as error:
        raise WiringError(f"cannot read config {path}: {error}") from error
    except json.JSONDecodeError as error:
        raise WiringError(f"invalid JSON in {path}: {error}") from error
    if not isinstance(data, dict):
        raise WiringError(f"config {path} must be a JSON object")
    return data


class ConfigFile:
    """A harness.json on disk, read and validated at construction."""

    def __init__(self, path: Path):
        self._path = Path(path).resolve()
        self._data = parse_config(self._path)

    @property
    def path(self) -> Path:
        return self._path

    @property
    def directory(self) -> Path:
        return self._path.parent

    def value(self, key, default=None):
        return self._data.get(key, default)

    def entries(self, key) -> list:
        return self._data.get(key) or []
