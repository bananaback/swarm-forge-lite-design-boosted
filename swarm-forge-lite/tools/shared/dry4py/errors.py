"""Failures the duplicate report can raise."""


class InvalidRegion(ValueError):
    """A code region with a missing path or an impossible line span."""


class InvalidDuplicate(ValueError):
    """A duplicate that joins a region to itself."""


class EmptyScope(ValueError):
    """A scan scope with no paths, or with paths that do not exist."""


class DetectorUnavailable(RuntimeError):
    """The clone detector could not be started."""


class DetectorError(RuntimeError):
    """The clone detector failed or returned an unusable report."""
