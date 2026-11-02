"""Make sure local state is ignored by the harness repository."""

from __future__ import annotations

from pathlib import Path

ENTRIES = ("config/pack.local.json", "local/", "tmp/")


def is_needed(pack: Path, config: dict) -> bool:
    ignore = pack / ".gitignore"
    text = ignore.read_text(encoding="utf-8") if ignore.is_file() else ""
    return any(entry not in text.splitlines() for entry in ENTRIES)


def apply(pack: Path, config: dict) -> None:
    ignore = pack / ".gitignore"
    text = ignore.read_text(encoding="utf-8") if ignore.is_file() else ""
    lines = text.splitlines()
    for entry in ENTRIES:
        if entry not in lines:
            lines.append(entry)
    ignore.write_text("\n".join(lines) + "\n", encoding="utf-8")
