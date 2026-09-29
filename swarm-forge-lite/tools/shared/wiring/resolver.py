"""Resolve config values against the config's directory."""

from dataclasses import dataclass
from pathlib import Path

from .errors import WiringError


@dataclass(frozen=True)
class PathResolver:
    """Turn raw config values into absolute paths."""

    base: Path

    def path(self, value) -> Path:
        candidate = Path(str(value)).expanduser()
        if candidate.is_absolute():
            return candidate.resolve()
        return (self.base / candidate).resolve()

    def optional_path(self, value) -> Path | None:
        return self.path(value) if value else None

    def paths(self, values) -> tuple:
        return tuple(self.path(value) for value in values)

    def persistent_tests(self, entries) -> tuple:
        resolved = []
        for entry in entries:
            if not isinstance(entry, dict) or "root" not in entry:
                raise WiringError("persistent_tests entries need a root")
            resolved.append(
                {"root": self.path(entry["root"]), "kind": entry.get("kind", "test")}
            )
        return tuple(resolved)
