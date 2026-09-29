#!/usr/bin/env python3
"""harness -- wiring status and cleanup for the swarm-forge-lite pack.

Usage:
  harness config            print resolved wiring as JSON
  harness status            print every resolved path and its existence
  harness clean [TARGET]    clean hot (default), state, artifacts, or all

The CLI is a thin composition root: it loads a PathSet (over wiring) and an
OsTree (over the filesystem), then dispatches to one command. Every rule about a
value lives on that value: CleanTarget owns the target table, OptionalRoot owns
absence, and the report value objects own their rendering.
"""

import argparse
import json
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import wiring

TARGET_NAMES: tuple = ("hot", "state", "artifacts", "all")
ABSENT_TEXT = "(none)"


class HarnessError(Exception):
    """The harness cannot resolve or act on the requested paths."""


@dataclass(frozen=True)
class OptionalRoot:
    """A resolved root that may be unconfigured; absence is a value, not None."""

    _path: Path | None = None

    def __post_init__(self) -> None:
        if self._path is not None and not isinstance(self._path, Path):
            raise HarnessError("optional root must be a Path or None")

    @classmethod
    def of(cls, path: Path | None) -> "OptionalRoot":
        return cls(path)

    def is_configured(self) -> bool:
        return self._path is not None

    def require(self) -> Path:
        if self._path is None:
            raise HarnessError("no root is configured")
        return self._path

    def text(self) -> str:
        return ABSENT_TEXT if self._path is None else str(self._path)


@dataclass(frozen=True)
class PersistentRoot:
    """One authored persistent-test root and its kind."""

    path: Path
    kind: str

    def __post_init__(self) -> None:
        if not isinstance(self.path, Path):
            raise HarnessError("persistent root path must be a Path")
        if not self.kind.strip():
            raise HarnessError("persistent root kind must not be blank")


@dataclass(frozen=True)
class CleanTarget:
    """A named set of disposable roots; owns the target-to-roots table."""

    name: str

    def __post_init__(self) -> None:
        if self.name not in TARGET_NAMES:
            raise HarnessError("unknown clean target: " + str(self.name))

    @classmethod
    def parse(cls, name: str) -> "CleanTarget":
        return cls(name)

    def roots(self, paths: "PathSet") -> tuple:
        hot = ("hot", paths.hot_tests())
        state = ("state", paths.state_root())
        artifacts = ("artifacts", paths.artifacts_root())
        table = {
            "hot": (hot,),
            "state": (state,),
            "artifacts": (artifacts,),
            "all": (hot, artifacts, state),
        }
        return table[self.name]


@dataclass(frozen=True)
class PathStatus:
    """One status line: a label, its resolved path text, and existence."""

    label: str
    text: str
    present: bool

    def __post_init__(self) -> None:
        if not self.label.strip():
            raise HarnessError("status label must not be blank")
        if not self.text.strip():
            raise HarnessError("status text must not be blank")

    def render(self) -> str:
        marker = "ok" if self.present else "-"
        return f"{self.label:<10} [{marker}] {self.text}"


@dataclass(frozen=True)
class StatusReport:
    """The ordered status lines for every resolved path."""

    rows: tuple

    def render_lines(self) -> tuple:
        return tuple(row.render() for row in self.rows)


@dataclass(frozen=True)
class ClearReport:
    """The outcome of clearing one disposable root."""

    label: str
    path: Path
    removed: int

    def __post_init__(self) -> None:
        if not self.label.strip():
            raise HarnessError("clear label must not be blank")
        if not isinstance(self.path, Path):
            raise HarnessError("clear path must be a Path")
        if self.removed < 0:
            raise HarnessError("removed count must not be negative")

    def render(self) -> str:
        plural = "y" if self.removed == 1 else "ies"
        return f"CLEANED {self.label}: {self.path} ({self.removed} entr{plural})"


class PathSet(Protocol):
    """The resolved paths the harness reads; implemented over wiring."""

    def pack_root(self) -> Path: ...
    def config_path(self) -> Path: ...
    def workspace_root(self) -> Path: ...
    def state_root(self) -> Path: ...
    def artifacts_root(self) -> Path: ...
    def hot_tests(self) -> Path: ...
    def features(self) -> OptionalRoot: ...
    def specs(self) -> OptionalRoot: ...
    def source_roots(self) -> tuple: ...
    def persistent_roots(self) -> tuple: ...
    def as_dict(self) -> dict: ...


class DisposableTree(Protocol):
    """The filesystem seam: query existence/children and clear a directory."""

    def exists(self, path: Path) -> bool: ...

    def count_entries(self, path: Path) -> int: ...

    def clear(self, path: Path) -> None: ...


class ResolvedWiring:
    """Adapt a wiring.Wiring to the PathSet port."""

    def __init__(self, resolved) -> None:
        self._resolved = resolved

    def pack_root(self) -> Path:
        return self._resolved.pack_root

    def config_path(self) -> Path:
        return self._resolved.config_path

    def workspace_root(self) -> Path:
        return self._resolved.workspace_root

    def state_root(self) -> Path:
        return self._resolved.state_root

    def artifacts_root(self) -> Path:
        return self._resolved.artifacts_root

    def hot_tests(self) -> Path:
        return self._resolved.hot_tests

    def features(self) -> OptionalRoot:
        return OptionalRoot.of(self._resolved.features)

    def specs(self) -> OptionalRoot:
        return OptionalRoot.of(self._resolved.specs)

    def source_roots(self) -> tuple:
        return tuple(self._resolved.source_roots)

    def persistent_roots(self) -> tuple:
        return tuple(
            PersistentRoot(entry["root"], entry["kind"])
            for entry in self._resolved.persistent_tests
        )

    def as_dict(self) -> dict:
        return self._resolved.as_dict()


class OsTree:
    """The real filesystem, behind the DisposableTree port."""

    def exists(self, path: Path) -> bool:
        return path.exists()

    def count_entries(self, path: Path) -> int:
        return len(list(path.iterdir())) if path.is_dir() else 0

    def clear(self, path: Path) -> None:
        path.mkdir(parents=True, exist_ok=True)
        for child in path.iterdir():
            if child.is_dir() and not child.is_symlink():
                shutil.rmtree(child)
            else:
                child.unlink()


def load_path_set(config: str | None) -> PathSet:
    """Resolve wiring and wrap it; raise HarnessError on a bad config."""
    try:
        resolved = wiring.load(config=config)
    except wiring.WiringError as error:
        raise HarnessError(str(error)) from error
    return ResolvedWiring(resolved)


def config_document(paths: PathSet) -> dict:
    """The JSON-ready document: exactly paths.as_dict()."""
    return paths.as_dict()


def status_report(paths: PathSet, tree: DisposableTree) -> StatusReport:
    """A row for every resolved path, in order."""
    rows = [
        _direct_row("PACK", paths.pack_root(), tree),
        _direct_row("CONFIG", paths.config_path(), tree),
        _direct_row("WORKSPACE", paths.workspace_root(), tree),
        _direct_row("STATE", paths.state_root(), tree),
        _direct_row("ARTIFACTS", paths.artifacts_root(), tree),
        _direct_row("HOT", paths.hot_tests(), tree),
        _optional_row("FEATURES", paths.features(), tree),
        _optional_row("SPECS", paths.specs(), tree),
    ]
    rows.extend(_direct_row("SOURCE", root, tree) for root in paths.source_roots())
    rows.extend(_persistent_row(root, tree) for root in paths.persistent_roots())
    return StatusReport(tuple(rows))


def _direct_row(label: str, path: Path, tree: DisposableTree) -> PathStatus:
    return PathStatus(label, str(path), tree.exists(path))


def _optional_row(label: str, root: OptionalRoot, tree: DisposableTree) -> PathStatus:
    if not root.is_configured():
        return PathStatus(label, ABSENT_TEXT, False)
    path = root.require()
    return PathStatus(label, str(path), tree.exists(path))


def _persistent_row(root: PersistentRoot, tree: DisposableTree) -> PathStatus:
    return PathStatus("PERSIST", f"{root.path} ({root.kind})", tree.exists(root.path))


def cmd_config(paths: PathSet) -> None:
    """Emit the config document as indented JSON."""
    print(json.dumps(config_document(paths), indent=2))


def cmd_status(paths: PathSet, tree: DisposableTree) -> None:
    """Emit one line per resolved path."""
    for line in status_report(paths, tree).render_lines():
        print(line)


def cmd_clean(target_name: str, paths: PathSet, tree: DisposableTree) -> None:
    """Clear the target's roots and emit one CLEANED line each."""
    target = CleanTarget.parse(target_name)
    for label, root in target.roots(paths):
        removed = tree.count_entries(root)
        tree.clear(root)
        print(ClearReport(label, root, removed).render())


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="harness")
    parser.add_argument("--config")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("config")
    sub.add_parser("status")

    clean = sub.add_parser("clean")
    clean.add_argument("target", nargs="?", choices=TARGET_NAMES, default="hot")
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        paths = load_path_set(args.config)
        tree = OsTree()
        if args.command == "config":
            cmd_config(paths)
        elif args.command == "status":
            cmd_status(paths, tree)
        else:
            cmd_clean(args.target, paths, tree)
    except HarnessError as error:
        print(f"harness: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
