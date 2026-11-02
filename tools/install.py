#!/usr/bin/env python3
"""Install this pack for one project: inspect, ask, apply.

    python3 tools/install.py inspect --root ../myproj
    python3 tools/install.py apply --answers install.json [--dry-run]

`inspect` writes a brief: what it found, what it recommends, what it cannot
decide. `apply` turns an answers file into `config/pack.local.json`, a design
folder and a `PROJECT.md`. Neither command ever prompts: an agent asks the
operator, then writes the answers down.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

PACK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACK / "tools" / "shared"))

import packconfig  # noqa: E402

SOURCE_CANDIDATES = ("app", "src")
DESIGN_FILES = ("runtime.json", "overlay.json", "policy.json")


def _git_root(path: Path) -> Path:
    result = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "--show-toplevel"],
        capture_output=True, text=True, check=False,
    )
    return Path(result.stdout.strip()) if result.returncode == 0 else path


def _first_dir(root: Path, names: tuple[str, ...]) -> str:
    for name in names:
        if (root / name).is_dir():
            return name
    return ""


def _specs(docs: Path) -> dict[str, str]:
    folder = docs / "specs"
    if not folder.is_dir():
        return {}
    return {
        path.name: path.stem.split("-", 1)[-1].replace("-", "_")
        for path in sorted(folder.glob("*.md"))
    }


def detect(root: Path) -> dict:
    """Facts, guesses and gaps for one project tree; never writes."""
    root = root.resolve()
    top = _git_root(root)
    source = _first_dir(top, SOURCE_CANDIDATES)
    docs = top / "docs"
    tests = top / "tests"
    acceptance = tests / "acceptance" / "run_acceptance.py"
    subsystems = []
    if source and (top / source).is_dir():
        for package in sorted(p for p in (top / source).iterdir() if p.is_dir()):
            if not package.name.startswith(("__", ".")):
                subsystems.append(
                    {"number": "", "label": package.name, "packages": [package.name]}
                )
    entry = {
        "project_root": os.path.relpath(top, PACK),
        "source_roots": [source] if source else [],
        "class_root": source,
        "test_paths": ["tests"] if tests.is_dir() else [],
        "unit_paths": "tests/unit" if (tests / "unit").is_dir() else "",
        "features": "tests/features" if (tests / "features").is_dir() else "",
        "docs_root": "docs" if docs.is_dir() else "",
        "design_root": "design",
        "specs": _specs(docs),
        "subsystems": subsystems,
        "acceptance_command": (
            "python3 tests/acceptance/run_acceptance.py"
            if acceptance.is_file()
            else ""
        ),
        "artifacts_root": f"<PACK>/tmp/{top.name}",
        "umlview": {
            "policy": "design/policy.json",
            "out": f"<PACK>/tmp/{top.name}/uml",
        },
    }
    certainties = {
        key: ("fact" if value else "missing") for key, value in entry.items()
    }
    for key in ("design_root", "artifacts_root", "umlview"):
        certainties[key] = "guess"
    questions = [key for key, value in certainties.items() if value == "missing"]
    return {
        "name": top.name.lower(),
        "root": str(top),
        "entry": entry,
        "certainties": certainties,
        "questions": questions,
    }


def brief(report: dict) -> str:
    lines = [
        f"# Install brief — {report['name']}",
        "",
        f"Detected root: `{report['root']}`",
        "",
        "| key | value | certainty |",
        "|---|---|---|",
    ]
    for key, value in report["entry"].items():
        shown = json.dumps(value) if not isinstance(value, str) else value
        lines.append(f"| `{key}` | `{shown}` | {report['certainties'][key]} |")
    lines += [
        "",
        "## Questions",
        "",
    ]
    lines += [f"- {question}" for question in report["questions"]] or ["- none"]
    lines += [
        "",
        "## Answers skeleton",
        "",
        "```json",
        json.dumps({"name": report["name"], "root": report["root"], **report["entry"]}, indent=2),
        "```",
    ]
    return "\n".join(lines) + "\n"


def apply_answers(pack: Path, answers: dict, dry_run: bool = False) -> list[str]:
    """Create the local config, the design folder and `PROJECT.md`."""
    actions: list[str] = []
    name = answers.get("name")
    root = answers.get("root")
    if not name or not root:
        raise ValueError("answers need `name` and `root`")
    project = Path(root).expanduser().resolve()

    config_file = pack / "config" / "pack.local.json"
    if config_file.is_file():
        config = json.loads(config_file.read_text(encoding="utf-8"))
    else:
        config = {"selector_env": "PACK_PROJECT", "default_project": name, "projects": {}}

    entry = {key: value for key, value in answers.items() if key not in {"name", "root"}}
    entry["project_root"] = os.path.relpath(project, pack)
    config["projects"][name] = entry
    if not config.get("default_project"):
        config["default_project"] = name
    actions.append(f"config: {config_file} (project {name})")

    design_root = entry.get("design_root")
    if design_root:
        target = project / design_root
        for filename in DESIGN_FILES:
            destination = target / filename
            if destination.exists():
                actions.append(f"kept: {destination}")
                continue
            source = pack / "examples" / "design" / filename
            actions.append(f"copy: {source} -> {destination}")
            if not dry_run:
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, destination)

    project_md = pack / "PROJECT.md"
    if not project_md.exists():
        actions.append(f"copy: PROJECT.md.example -> {project_md}")
        if not dry_run:
            shutil.copy2(pack / "PROJECT.md.example", project_md)

    scratch = pack / "tmp" / name
    actions.append(f"mkdir: {scratch}")
    if not dry_run:
        scratch.mkdir(parents=True, exist_ok=True)

    if not dry_run:
        config_file.parent.mkdir(parents=True, exist_ok=True)
        config_file.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
        ignore = pack / ".gitignore"
        line = "config/pack.local.json"
        if ignore.is_file() and line not in ignore.read_text(encoding="utf-8").splitlines():
            ignore.write_text(ignore.read_text(encoding="utf-8").rstrip("\n") + f"\n{line}\n", encoding="utf-8")
    return actions


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    inspect = commands.add_parser("inspect", help="detect and write a brief")
    inspect.add_argument("--root", required=True)
    inspect.add_argument("--name", default="")
    inspect.add_argument("--json", action="store_true")
    apply = commands.add_parser("apply", help="install from an answers file")
    apply.add_argument("--answers", required=True)
    apply.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    if args.command == "inspect":
        report = detect(Path(args.root))
        if args.name:
            report["name"] = args.name
        text = brief(report)
        scratch = PACK / "tmp"
        scratch.mkdir(parents=True, exist_ok=True)
        (scratch / "install-brief.md").write_text(text, encoding="utf-8")
        print(json.dumps(report, indent=2) if args.json else text)
        return 0

    try:
        answers = json.loads(Path(args.answers).read_text(encoding="utf-8"))
        for action in apply_answers(PACK, answers, dry_run=args.dry_run):
            print(action)
    except (OSError, ValueError, KeyError) as error:
        print(f"install: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
