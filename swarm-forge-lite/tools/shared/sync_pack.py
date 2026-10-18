#!/usr/bin/env python3
"""sync_pack -- copy the pack-owned files from this pack to a clone.

Dry run by default: print every file that differs. `--apply` copies only the
allowlisted pack-owned files and never deletes. Project-owned files
(`harness.json`, `PROJECT.md`, `design/subsystems/`) never travel.

The clone is a ship root that contains `swarm-forge-lite/`:

    python3 swarm-forge-lite/tools/shared/sync_pack.py --to ../tdd_harness
    python3 swarm-forge-lite/tools/shared/sync_pack.py --to ../tdd_harness --apply

A change that needs a deletion or a conflict decision is reported and stops.
Run the clone tests with `--apply`; they use the clone's selftest config.
"""

from __future__ import annotations

import argparse
import filecmp
import shutil
import subprocess
import sys
from pathlib import Path

PACK = Path(__file__).resolve().parents[2]
SHIP = PACK.parent
PACK_NAME = PACK.name

PACK_ROOTS = (
    "tools",
    "protocol",
    "reference",
    "constitution",
    "harness_tests",
    "project_tests",
)

PACK_FILES = (
    "harness.selftest.json",
    "WIRING.md",
    "PUBLISH-DOCS.md",
)

SHIP_FILES = (
    "INSTALL.md",
    "UPDATE.md",
    "HARNESS_SELF_IMPROVEMENT.md",
    ".gitignore",
)

SKIP_DIRS = {
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".hypothesis",
    ".git",
    ".codegraph",
    "dump",
    ".swarmforge",
    "hot_tests",
    "node_modules",
}

SKIP_NAMES = {".DS_Store"}


def _files_under(root: Path) -> list[Path]:
    if not root.exists():
        return []
    if root.is_file():
        return [root]
    out = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if path.name in SKIP_NAMES:
            continue
        if any(part in SKIP_DIRS for part in path.relative_to(root).parts):
            continue
        out.append(path)
    return sorted(out)


def owned_files(ship: Path = SHIP) -> list[Path]:
    """Every file the clone may receive, in a stable order."""
    pack = ship / PACK_NAME
    out: list[Path] = []
    for name in PACK_ROOTS:
        out.extend(_files_under(pack / name))
    for name in PACK_FILES:
        out.extend(_files_under(pack / name))
    for name in SHIP_FILES:
        out.extend(_files_under(ship / name))
    out.extend(_files_under(ship / ".opencode" / "plugins"))
    return out


def changes(ship: Path, target: Path) -> tuple[list[tuple[str, Path]], list[Path]]:
    """(action, path) pairs for files that differ, and files only in the target.

    Actions: `add` (no target file), `update` (bytes differ). A file only in the
    target is reported, never deleted.
    """
    source_files = owned_files(ship)
    out: list[tuple[str, Path]] = []
    expected: set[Path] = set()
    for source in source_files:
        destination = target / source.relative_to(ship)
        expected.add(destination)
        if not destination.exists():
            out.append(("add", source))
        elif not filecmp.cmp(source, destination, shallow=False):
            out.append(("update", source))
    extra = [path for path in owned_files(target) if path not in expected]
    return out, extra


def apply_changes(ship: Path, target: Path, rows: list[tuple[str, Path]]) -> list[Path]:
    written = []
    for _action, source in rows:
        destination = target / source.relative_to(ship)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        written.append(destination)
    return written


def verify(target: Path) -> tuple[bool, str]:
    """Run the clone's self-tests through its lane wrapper."""
    pack = target / PACK_NAME
    lane = pack / "tools" / "shared" / "lane"
    selftest = pack / "harness.selftest.json"
    if not lane.is_file() or not selftest.is_file():
        return False, f"no lane or selftest config under {pack}"
    result = subprocess.run(
        [
            str(lane),
            "--config",
            str(selftest),
            "harness",
            "bash",
            "-c",
            "cd harness_tests && python3 -m pytest -q",
        ],
        cwd=str(pack),
        capture_output=True,
        text=True,
        check=False,
    )
    tail = (result.stdout or result.stderr).strip().splitlines()
    return result.returncode == 0, tail[-1] if tail else "no output"


def _resolve_target(raw: str) -> Path:
    target = Path(raw).expanduser().resolve()
    if (target / PACK_NAME / "harness.json").is_file():
        return target
    if target.name == PACK_NAME and (target / "harness.json").is_file():
        return target.parent
    raise SystemExit(f"sync: {target} does not contain {PACK_NAME}/harness.json")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="sync_pack")
    parser.add_argument("--to", required=True, help="The clone ship root.")
    parser.add_argument(
        "--apply", action="store_true", help="Copy the files (default: dry run)."
    )
    parser.add_argument(
        "--no-verify", action="store_true", help="Skip the clone self-tests."
    )
    args = parser.parse_args(argv)

    target = _resolve_target(args.to)
    rows, extra = changes(SHIP, target)
    if not rows and not extra:
        print(f"sync: {target} is current for the pack-owned files")
        return 0
    verb = "apply" if args.apply else "dry run"
    print(f"sync ({verb}): {len(rows)} file(s) differ")
    for action, source in rows:
        print(f"  {action:<6} {source.relative_to(SHIP)}")
    for path in extra:
        print(f"  only in target (not deleted): {path.relative_to(target)}")
    if not args.apply:
        print("Nothing written. Re-run with --apply.")
        return 0

    written = apply_changes(SHIP, target, rows)
    print(f"wrote {len(written)} file(s) under {target}")
    if not args.no_verify:
        ok, line = verify(target)
        print(f"clone tests: {'pass' if ok else 'fail'} — {line}")
        if not ok:
            return 1
    print("Next: review the diff, commit, push, then update .harness-version.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
