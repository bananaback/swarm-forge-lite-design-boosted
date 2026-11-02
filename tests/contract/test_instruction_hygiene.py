"""Rule 33 — the general tier carries no project, host or toolchain name.

The protocol ships to every project and every host, so a project name, an
absolute path, a host product or a language tool in it is a leak that makes the
pack unusable elsewhere. This test is the mechanical guard: it fails the moment
one appears.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

PACK = Path(__file__).resolve().parents[2]

TIER = [
    PACK / "README.md",
    *sorted((PACK / "protocol").glob("*.md")),
    *sorted((PACK / "constitution").rglob("*.md")),
]
TIER += [p for p in (PACK / "INSTALL.md", PACK / "CONTRIBUTING.md") if p.is_file()]

FORBIDDEN = {
    "project name": r"\b(deepstream|control-server|ds91|whalm)\b",
    "host product": r"\b(deepseek|opencode|claude|commandcode)\b",
    "language tool": r"\b(pytest|ruff|dryer|crapper)\b",
    "absolute path": r"/home/",
}


def _label(path: Path) -> str:
    try:
        return str(path.relative_to(PACK))
    except ValueError:
        return path.name


def _hits(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    found = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        for label, pattern in FORBIDDEN.items():
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                found.append(
                    f"{_label(path)}:{line_number}: {label} "
                    f"{match.group(0)!r} — {line.strip()[:80]}"
                )
    return found


def test_the_general_tier_names_no_project_host_or_toolchain():
    problems = [problem for path in TIER for problem in _hits(path)]

    assert not problems, "leaks in the general tier:\n" + "\n".join(problems)


def test_the_guard_would_catch_a_leak(tmp_path):
    leaked = tmp_path / "leak.md"
    leaked.write_text("Run pytest in /home/me/project for deepstream.\n", encoding="utf-8")

    problems = _hits(leaked)

    assert len(problems) == 3
