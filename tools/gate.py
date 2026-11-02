#!/usr/bin/env python3
"""Run one named gate from the project config.

The protocol names **gates** — `lint`, `format_check`, `unit`, `acceptance`,
`coverage`, `lcov`, `dry`, `crap` — and the project maps a gate to the command
that implements it. That is what keeps the harness language-neutral: a project
that does not use Python changes its config, not the role prompts.

    python3 tools/gate.py unit
    python3 tools/gate.py dry --dry-run
    python3 tools/gate.py --list

The gate's exit code is returned unchanged, so a caller can trust it exactly as
it would trust the underlying tool.
"""

from __future__ import annotations

import argparse
import os
import shlex
import subprocess
import sys
from pathlib import Path

PACK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACK / "tools" / "shared"))

import packconfig  # noqa: E402

PROJECT_TOKEN = "<PROJECT>"
DEFAULTS_NOTE = "built from the project config"

# A gate that depends on an optional capability refuses to run when the project
# disabled it, so a disabled check can never look like a passing one.
CAPABILITY = {"dry": "duplication", "crap": "crap", "acceptance": "gherkin"}


def _default_gates(project: Path, entry: dict) -> dict[str, list[str]]:
    """The Python reference implementation, derived from the project entry."""
    artifacts = (project / entry.get("artifacts_root", "tmp")).resolve()
    lint = entry.get("lint_paths", ".")
    unit = entry.get("unit_paths", "tests/unit")
    gates = {
        "lint": ["ruff", "check", lint],
        "format_check": ["ruff", "format", "--check", lint],
        "unit": ["python3", "-m", "pytest", "-q", unit],
    }
    sources = entry.get("source_roots") or []
    if sources:
        source = (project / sources[0]).resolve()
        gates["dry"] = [
            "python3", "-m", "dryer",
            "--root", str(artifacts),
            "--source-root", str(source),
            "--threshold", "0.82", "--min-lines", "4", "--min-nodes", "20",
        ]
        gates["crap"] = [
            "python3", "-m", "crapper",
            "--root", str(artifacts),
            "--use-existing-coverage",
            "--source-root", str(source),
            "--threshold", "10",
        ]
        gates["coverage"] = [
            "python3", "-m", "coverage", "run",
            "--data-file", str(artifacts / ".coverage"),
            "-m", "pytest", "-q", unit,
        ]
        gates["lcov"] = [
            "python3", "-m", "coverage", "lcov",
            "--data-file", str(artifacts / ".coverage"),
            "-o", str(artifacts / "target" / "coverage" / "python" / "lcov.info"),
        ]
    acceptance = entry.get("acceptance_command")
    if acceptance:
        gates["acceptance"] = shlex.split(acceptance)
    return gates


def resolve(
    project: Path, entry: dict
) -> dict[str, tuple[list[str], str]]:
    """Every gate as (command, where it came from). Config overrides defaults."""
    gates = {name: (cmd, DEFAULTS_NOTE) for name, cmd in _default_gates(project, entry).items()}
    for name, value in (entry.get("gates") or {}).items():
        command = shlex.split(value) if isinstance(value, str) else list(value)
        gates[name] = (command, "config/pack.gates")
    return gates


def _expand(command: list[str], project: Path) -> list[str]:
    return [part.replace(PROJECT_TOKEN, str(project)) for part in command]


def _environment(name: str, entry: dict, project: Path) -> dict[str, str]:
    environment = dict(os.environ)
    environment["PACK_PROJECT"] = name
    extra = [str(PACK / "tools" / "shared"), str(PACK / "tools" / "refactorer")]
    existing = environment.get("PYTHONPATH", "")
    environment["PYTHONPATH"] = os.pathsep.join([*extra, existing]) if existing else os.pathsep.join(extra)
    for key, value in (entry.get("gate_env") or {}).items():
        environment[key] = str(value).replace(PROJECT_TOKEN, str(project))
    return environment


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("gate", nargs="?", help="gate name to run")
    parser.add_argument("--project", default="", help="project name; default: PACK_PROJECT")
    parser.add_argument("--list", action="store_true", help="print the gate names")
    parser.add_argument("--dry-run", action="store_true", help="print the command, run nothing")
    args = parser.parse_args(argv)

    try:
        config = packconfig.load(PACK)
        if args.project:
            os.environ["PACK_PROJECT"] = args.project
        name, _ = packconfig.select(config)
    except packconfig.ConfigError as error:
        print(f"gate: {error}", file=sys.stderr)
        return 1

    entry = config["projects"][name]
    project = (PACK / entry["project_root"]).resolve()
    if not project.is_dir():
        print(f"gate: project tree not found: {project}", file=sys.stderr)
        return 1
    gates = resolve(project, entry)

    if args.list or not args.gate:
        print("\n".join(sorted(gates)))
        return 0
    capability = CAPABILITY.get(args.gate)
    if capability and (entry.get("capabilities") or {}).get(capability) is False:
        print(
            f"gate: capability {capability!r} is disabled for project {name}",
            file=sys.stderr,
        )
        return 1
    if args.gate not in gates:
        print(
            f"gate: unknown gate {args.gate!r}; known: {', '.join(sorted(gates))}",
            file=sys.stderr,
        )
        return 1

    command, origin = gates[args.gate]
    command = _expand(command, project)
    workdir = (project / entry.get("gates_cwd", ".")).resolve()
    print(
        f"gate={args.gate} project={name} origin={origin} cwd={workdir}\n"
        f"command: {' '.join(command)}",
        file=sys.stderr,
    )
    if args.dry_run:
        return 0
    if not workdir.is_dir():
        print(f"gate: gate working directory not found: {workdir}", file=sys.stderr)
        return 1
    return subprocess.call(command, cwd=workdir, env=_environment(name, entry, project))


if __name__ == "__main__":
    raise SystemExit(main())
