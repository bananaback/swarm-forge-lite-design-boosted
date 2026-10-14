"""A readable unified diff of two model states."""

from __future__ import annotations

import difflib

from .model import dumps


def render(before: dict, after: dict, style=None) -> str:
    """The unified diff of the text of two models (empty when equal)."""
    old = dumps(before, style).splitlines()
    new = dumps(after, style).splitlines()
    return "\n".join(
        difflib.unified_diff(old, new, fromfile="before", tofile="after", lineterm="")
    )
