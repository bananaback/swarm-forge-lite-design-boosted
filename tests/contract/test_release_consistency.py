"""Rule I7 — version, changelog and migrations move together."""

from __future__ import annotations

import re
from pathlib import Path

PACK = Path(__file__).resolve().parents[2]


def test_a_version_file_exists_and_is_semver():
    version = (PACK / "VERSION").read_text(encoding="utf-8").strip()

    assert re.fullmatch(r"\d+\.\d+\.\d+", version), version


def test_the_changelog_documents_the_current_version():
    version = (PACK / "VERSION").read_text(encoding="utf-8").strip()
    changelog = (PACK / "CHANGELOG.md").read_text(encoding="utf-8")

    assert f"## {version}" in changelog


def test_migrations_are_numbered_once_and_in_order():
    files = sorted((PACK / "migrations").glob("*.py"))
    numbers = [int(path.name.split("_", 1)[0]) for path in files]

    assert numbers == list(range(1, len(numbers) + 1)), numbers
