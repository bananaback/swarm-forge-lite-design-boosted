#!/usr/bin/env python3
"""One command before pushing a harness change.

    python3 tools/selftest.py            # contract suite + doctor + design gates
    python3 tools/selftest.py --gates    # also lint, format_check and unit per project

Red anywhere means the change is not done. This is the harness's own terminal
gate, the same shape the architect runs for a project.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

PACK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACK / "tools" / "shared"))

import packconfig  # noqa: E402


def _run(command: list[str], project: str = "") -> tuple[int, str]:
    environment = dict(os.environ)
    if project:
        environment["PACK_PROJECT"] = project
    result = subprocess.run(
        command, cwd=PACK, capture_output=True, text=True, env=environment, check=False
    )
    tail = (result.stdout + result.stderr).strip().splitlines()
    return result.returncode, tail[-1] if tail else ""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gates", action="store_true", help="also run lint, format and unit")
    parser.add_argument("--coverage", action="store_true", help="run the suite under the coverage gate")
    args = parser.parse_args(argv)

    version = (PACK / "VERSION").read_text(encoding="utf-8").strip() if (PACK / "VERSION").is_file() else "?"
    print(f"harness {version}  ({PACK})")

    rows: list[tuple[str, int, str]] = []
    if (PACK / "tests").is_dir() and args.coverage:
        data = str(PACK / "tmp" / ".coverage")
        code, message = _run([
            sys.executable, "-m", "coverage", "run", "--data-file", data,
            "-m", "pytest", "-q", "tests/",
        ])
        rows.append(("contract suite", code, message))
        code, message = _run([
            sys.executable, "-m", "coverage", "report",
            "--data-file", data, "--fail-under", "90",
        ])
        rows.append(("coverage gate", code, message))
    elif (PACK / "tests").is_dir():
        code, message = _run([sys.executable, "-m", "pytest", "-q", "tests/"])
        rows.append(("contract suite", code, message))

    try:
        config = packconfig.load(PACK)
        projects = sorted(config.get("projects") or {})
    except packconfig.ConfigError as error:
        print(f"FAIL config: {error}")
        return 1

    for project in projects:
        code, message = _run([sys.executable, str(PACK / "tools" / "doctor.py")], project)
        rows.append((f"doctor {project}", code, message))
        for domain in ("classes", "runtime", "docs"):
            code, message = _run(
                [sys.executable, str(PACK / "tools" / "design" / "arch.py"), domain, "validate"],
                project,
            )
            rows.append((f"{domain} {project}", code, message))
        if args.gates:
            for gate in ("lint", "format_check", "unit"):
                code, message = _run(
                    [sys.executable, str(PACK / "tools" / "gate.py"), gate], project
                )
                rows.append((f"{gate} {project}", code, message))

    failed = 0
    for name, code, message in rows:
        print(f"{'ok  ' if code == 0 else 'FAIL'} {name}: {message}")
        failed += code != 0
    print(f"\n{len(rows)} steps, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
