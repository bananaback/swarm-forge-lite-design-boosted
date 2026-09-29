"""Frozen value objects: the scan request and the duplicate report."""

from dataclasses import dataclass
from pathlib import Path

from .errors import EmptyScope, InvalidDuplicate, InvalidRegion


@dataclass(frozen=True)
class CodeRegion:
    """One span of source, identified by file path and inclusive line range."""

    path: Path
    start: int
    end: int

    def __post_init__(self):
        if not str(self.path):
            raise InvalidRegion("path is required")
        if self.start < 1:
            raise InvalidRegion("start line must be >= 1")
        if self.end < self.start:
            raise InvalidRegion("end line must be >= start line")

    def line_count(self):
        return self.end - self.start + 1


@dataclass(frozen=True)
class Duplicate:
    """Two regions that hold the same code."""

    first: CodeRegion
    second: CodeRegion

    def __post_init__(self):
        if self.first == self.second:
            raise InvalidDuplicate("a duplicate joins two distinct regions")


@dataclass(frozen=True)
class DuplicateReport:
    """The duplicates found in one scan; empty means clean."""

    duplicates: tuple = ()

    def is_empty(self):
        return not self.duplicates

    def count(self):
        return len(self.duplicates)


@dataclass(frozen=True)
class ScanScope:
    """The files, directories, and thresholds a scan will cover."""

    paths: tuple
    min_lines: int = 4
    min_tokens: int = 50

    def __post_init__(self):
        if not self.paths:
            raise EmptyScope("at least one path is required")
        if self.min_lines < 1:
            raise EmptyScope("min_lines must be >= 1")
        if self.min_tokens < 1:
            raise EmptyScope("min_tokens must be >= 1")
        missing = [str(path) for path in self.paths if not Path(path).exists()]
        if missing:
            raise EmptyScope("paths not found: " + ", ".join(missing))
