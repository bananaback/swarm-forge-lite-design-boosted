"""The resolved path set handed to the tools."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Wiring:
    """Every resolved path a tool needs."""

    pack_root: Path
    workspace_root: Path
    state_root: Path
    artifacts_root: Path
    hot_tests: Path
    persistent_tests: tuple
    source_roots: tuple
    features: Path | None
    specs: Path | None
    config_path: Path

    def as_dict(self) -> dict:
        return {
            "pack_root": str(self.pack_root),
            "workspace_root": str(self.workspace_root),
            "state_root": str(self.state_root),
            "artifacts_root": str(self.artifacts_root),
            "hot_tests": str(self.hot_tests),
            "persistent_tests": [
                {"root": str(entry["root"]), "kind": entry["kind"]}
                for entry in self.persistent_tests
            ],
            "source_roots": [str(path) for path in self.source_roots],
            "features": str(self.features) if self.features else None,
            "specs": str(self.specs) if self.specs else None,
            "config_path": str(self.config_path),
        }
