"""Failures the ruff check can raise."""


class InvalidUsage(ValueError):
    """The caller passed arguments the wrapper cannot accept."""


class InvalidConfiguration(ValueError):
    """The cache location is unusable."""


class ToolUnavailable(RuntimeError):
    """The ruff executable could not be found or started."""
