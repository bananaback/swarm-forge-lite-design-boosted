"""Resolve config values against the config's directory.

An unwired pack names no project. It carries the placeholder `<PROJECT_ROOT>`
wherever a project path belongs, and the placeholder resolves from the
environment: `<PROJECT_ROOT>` reads `SWARM_PROJECT`. A wired pack has no
placeholder left. The contract is in `WIRING.md`.
"""

import os
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from .errors import WiringError

TOKEN = re.compile(r"<([A-Z][A-Z0-9_]*)>")

# The placeholder contract: one token, one variable.
TOKEN_ENV = {"PROJECT_ROOT": "SWARM_PROJECT"}


@dataclass(frozen=True)
class PathResolver:
    """Turn raw config values into absolute paths, and resolve placeholders."""

    base: Path
    environ: Mapping | None = None

    def _value(self, token: str) -> str:
        """The value of one placeholder token, from the environment."""
        variable = TOKEN_ENV.get(token)
        if variable is None:
            known = ", ".join(f"<{name}>" for name in sorted(TOKEN_ENV))
            raise WiringError(
                f"unknown placeholder <{token}>; known placeholders: {known}"
            )
        environ = os.environ if self.environ is None else self.environ
        found = environ.get(variable)
        if not found:
            raise WiringError(
                f"the pack is not wired: <{token}> is unresolved. "
                f"Set {variable}=<path to the project>, or wire the pack - see WIRING.md."
            )
        return found

    def _expand(self, value) -> str:
        """Replace every placeholder token in one raw config value."""
        return TOKEN.sub(lambda match: self._value(match.group(1)), str(value))

    def path(self, value) -> Path:
        candidate = Path(self._expand(value)).expanduser()
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
