#!/usr/bin/env python3
"""Copy authored design data from the legacy pack location into the project.

Additive only: this tool never moves, overwrites or deletes. It is run after a
project's config gains `design_root`, and it is safe to run twice.

    python3 tools/migrate.py            # copy what is missing
    python3 tools/migrate.py --dry-run  # print the plan, write nothing
    python3 tools/migrate.py --project <name>
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

PACK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACK / "tools" / "shared"))

import packconfig  # noqa: E402


def _legacy_projects(pack: Path) -> dict:
    """The old config's project entries, for paths this one no longer names."""
    legacy = pack / "config" / "pack.json"
    if not legacy.is_file():
        return {}
    try:
        return json.loads(legacy.read_text(encoding="utf-8")).get("projects", {})
    except (OSError, ValueError):
        return {}


def _targets(
    pack: Path, name: str, entry: dict, legacy_entry: dict | None = None
) -> list[tuple[Path, Path]]:
    """(source, destination) pairs for one project, legacy to project-owned."""
    design_root = entry.get("design_root")
    if not design_root:
        return []
    project = (pack / entry["project_root"]).resolve()
    target = (project / design_root).resolve()
    old_policy = (
        (legacy_entry or {}).get("umlview", {}).get("policy")
        or "umlview.json"
    )
    return [
        (pack / "architecture" / name / "runtime.json", target / "runtime.json"),
        (pack / "architecture" / name / "design.json", target / "overlay.json"),
        (project / old_policy, target / "policy.json"),
    ]


def plan(pack: Path, config: dict, names: list[str]) -> list[tuple[str, str, Path]]:
    """Return (project, action, path) rows; no filesystem changes."""
    rows: list[tuple[str, str, Path]] = []
    projects = config.get("projects", {})
    legacy = _legacy_projects(pack)
    for name in names:
        entry = projects[name]
        if not entry.get("design_root"):
            rows.append((name, "skip: no design_root, legacy path stays", pack))
            continue
        for source, destination in _targets(pack, name, entry, legacy.get(name)):
            if not source.is_file():
                rows.append((name, "absent", source))
            elif destination.exists():
                rows.append((name, "kept: destination exists", destination))
            else:
                rows.append((name, f"copy -> {destination}", source))
    return rows


def apply(pack: Path, config: dict, names: list[str]) -> list[tuple[str, str, Path]]:
    """Perform the copies the plan named, parent folders included."""
    rows = []
    legacy = _legacy_projects(pack)
    for name in names:
        entry = config["projects"][name]
        for source, destination in _targets(pack, name, entry, legacy.get(name)):
            if not source.is_file():
                rows.append((name, "absent", source))
                continue
            if destination.exists():
                rows.append((name, "kept: destination exists", destination))
                continue
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
            rows.append((name, f"copied -> {destination}", destination))
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="", help="config file override")
    parser.add_argument("--project", action="append", default=[])
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    try:
        config = packconfig.load(PACK, override=args.config or None)
    except packconfig.ConfigError as error:
        print(f"migrate: {error}", file=sys.stderr)
        return 1

    projects = config.get("projects", {})
    names = args.project or sorted(projects)
    unknown = [name for name in names if name not in projects]
    if unknown:
        print(f"migrate: unknown project(s): {', '.join(unknown)}", file=sys.stderr)
        return 1

    rows = plan(PACK, config, names) if args.dry_run else apply(PACK, config, names)
    for name, action, path in rows:
        print(f"{name:20} {action}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
