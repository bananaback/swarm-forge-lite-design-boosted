#!/usr/bin/env python3
"""Bring an installed harness forward without breaking the project.

    python3 tools/update.py check          # read-only report, refuses on dirty
    python3 tools/update.py trial          # new harness against this project, disposable
    python3 tools/update.py apply --yes    # migrations, fast-forward, gates, record

There is no automatic pull. `check` is always safe; `trial` touches only a
worktree under `local/trial`; `apply` needs `--yes` and never runs without it.
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

PACK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACK / "tools" / "shared"))

import packconfig  # noqa: E402

LEGACY_PATHS = ("config/pack.json", "architecture/")
STATE = Path("local") / "harness.json"
MIGRATIONS = "migrations"


def _git(pack: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(pack), *args], capture_output=True, text=True, check=False
    )


def _branch(pack: Path) -> str:
    return _git(pack, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()


def read_state(pack: Path) -> dict:
    path = pack / STATE
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def write_state(pack: Path, state: dict) -> None:
    path = pack / STATE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")


def risk_of(path: str) -> str:
    if path.startswith(LEGACY_PATHS):
        return "legacy"
    if path.startswith(MIGRATIONS + "/"):
        return "migration"
    if path.startswith("tests/") or path.startswith(".github/"):
        return "tests"
    if path.startswith(("protocol/", "tools/", "constitution/", "hosts/")):
        return "behavior"
    return "docs"


def dirty_files(pack: Path) -> list[str]:
    result = _git(pack, "status", "--porcelain")
    return [
        line[3:]
        for line in result.stdout.splitlines()
        if line and not line.startswith("??")
    ]


def check(pack: Path, offline: bool = False) -> dict:
    result = {"error": "", "commits": [], "files": [], "dirty": [], "diverged": False}
    if not (pack / ".git").exists():
        result["error"] = "not a git checkout"
        return result
    result["dirty"] = dirty_files(pack)
    if not offline:
        fetched = _git(pack, "fetch", "--quiet", "origin")
        if fetched.returncode != 0:
            result["error"] = f"git fetch failed: {fetched.stderr.strip()}"
            return result
    branch = _branch(pack)
    target = f"origin/{branch}"
    if _git(pack, "rev-parse", "--verify", "--quiet", target).returncode != 0:
        result["error"] = f"no upstream branch {target}"
        return result
    state = read_state(pack)
    base = state.get("commit") or _git(pack, "merge-base", "HEAD", target).stdout.strip()
    result["base"] = base
    result["target"] = _git(pack, "rev-parse", target).stdout.strip()
    result["diverged"] = _git(pack, "merge-base", "--is-ancestor", "HEAD", target).returncode != 0
    result["commits"] = [
        line
        for line in _git(pack, "log", "--oneline", f"{base}..{target}").stdout.splitlines()
        if line
    ]
    raw = _git(pack, "diff", "--name-status", f"{base}..{target}").stdout
    for line in raw.splitlines():
        status, _, path = line.partition("\t")
        if path:
            result["files"].append({"status": status[:1], "path": path, "risk": risk_of(path)})
    return result


def report(result: dict) -> str:
    lines = []
    if result["error"]:
        return f"error: {result['error']}\n"
    if result["dirty"]:
        lines.append("dirty: these harness files are modified; upstream them first:")
        lines.extend(f"  {path}" for path in result["dirty"])
    if result["diverged"]:
        lines.append("diverged: local commits are not on origin; resolve before applying")
    if not result["commits"]:
        lines.append("up to date.")
        return "\n".join(lines) + "\n"
    lines.append(f"{len(result['commits'])} commit(s) available:")
    lines.extend(f"  {commit}" for commit in result["commits"])
    by_risk: dict[str, list[str]] = {}
    for file in result["files"]:
        by_risk.setdefault(file["risk"], []).append(f"{file['status']} {file['path']}")
    lines.append("")
    for risk in ("docs", "tests", "behavior", "migration", "legacy"):
        if risk in by_risk:
            lines.append(f"{risk}:")
            lines.extend(f"  {entry}" for entry in by_risk[risk])
    return "\n".join(lines) + "\n"


def _projects(config: dict) -> list[str]:
    projects = config.get("projects") or {}
    return sorted(projects) or []


def _run_tool(tool: Path, args: list[str], config_path: Path, project: str) -> tuple[int, str]:
    environment = dict(os.environ)
    environment["SWARM_CONFIG"] = str(config_path)
    environment["PACK_PROJECT"] = project
    result = subprocess.run(
        [sys.executable, str(tool), *args],
        capture_output=True, text=True, env=environment, check=False,
    )
    return result.returncode, (result.stdout + result.stderr).strip()


def trial(pack: Path) -> list[tuple[str, int, str]]:
    """Run the upstream harness against this project, then remove the worktree."""
    check_result = check(pack, offline=True)
    if check_result.get("error"):
        raise RuntimeError(check_result["error"])
    target = check_result.get("target")
    if not target:
        raise RuntimeError("no upstream target to trial")
    worktree = pack / "local" / "trial"
    if worktree.exists():
        subprocess.run(["git", "-C", str(pack), "worktree", "remove", "--force", str(worktree)], check=False)
        shutil.rmtree(worktree, ignore_errors=True)
    add = _git(pack, "worktree", "add", "--detach", str(worktree), target)
    if add.returncode != 0:
        raise RuntimeError(add.stderr.strip())
    config = packconfig.load(pack)
    config_path = packconfig.config_path(pack)
    rows: list[tuple[str, int, str]] = []
    try:
        for project in _projects(config):
            code, output = _run_tool(worktree / "tools" / "doctor.py", ["--project", project], config_path, project)
            rows.append((f"doctor {project}", code, output.splitlines()[-1] if output else ""))
            for gate in ("classes", "runtime", "docs"):
                code, output = _run_tool(
                    worktree / "tools" / "design" / "arch.py", [gate, "validate"], config_path, project
                )
                rows.append((f"{gate} {project}", code, output.splitlines()[-1] if output else ""))
    finally:
        subprocess.run(["git", "-C", str(pack), "worktree", "remove", "--force", str(worktree)], check=False)
        shutil.rmtree(worktree, ignore_errors=True)
    return rows


def _migrations(pack: Path) -> list[Path]:
    folder = pack / MIGRATIONS
    return sorted(folder.glob("[0-9]*.py")) if folder.is_dir() else []


def run_migrations(pack: Path, config: dict) -> list[str]:
    applied = []
    state = read_state(pack)
    done = list(state.get("migrations") or [])
    for path in _migrations(pack):
        name = path.stem
        if name in done:
            continue
        module = sys.modules.get(name)
        if module is None:
            import importlib.util

            spec = importlib.util.spec_from_file_location(name, path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
        if getattr(module, "is_needed", lambda pack, config: True)(pack, config):
            module.apply(pack, config)
        done.append(name)
        applied.append(name)
    state["migrations"] = done
    write_state(pack, state)
    return applied


def apply(pack: Path, config: dict, yes: bool) -> int:
    if not yes:
        print(report(check(pack, offline=True)))
        print("not applied: pass --yes")
        return 0
    current = check(pack)
    if current["error"]:
        print(current["error"], file=sys.stderr)
        return 1
    if current["dirty"]:
        print(report(current), file=sys.stderr)
        print("refused: dirty harness files", file=sys.stderr)
        return 1
    if current["diverged"]:
        print(report(current), file=sys.stderr)
        print("refused: diverged from origin", file=sys.stderr)
        return 1
    applied = run_migrations(pack, config)
    if applied:
        print("migrations: " + ", ".join(applied))
    merged = _git(pack, "merge", "--ff-only", current["target"])
    print(merged.stdout.strip() or merged.stderr.strip())
    if merged.returncode != 0:
        return 1
    write_state(pack, {
        "commit": current["target"],
        "updated_at": datetime.date.today().isoformat(),
        "migrations": list(read_state(pack).get("migrations") or []),
    })
    failed = 0
    config = packconfig.load(pack)
    config_path = packconfig.config_path(pack)
    for project in _projects(config):
        code, output = _run_tool(pack / "tools" / "doctor.py", ["--project", project], config_path, project)
        print(f"doctor {project}: exit {code}")
        failed += code != 0
        for gate in ("classes", "runtime", "docs"):
            code, output = _run_tool(pack / "tools" / "design" / "arch.py", [gate, "validate"], config_path, project)
            print(f"{gate} {project}: exit {code} {output.splitlines()[-1] if output else ''}")
            failed += code != 0
    return 1 if failed else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("check", "trial", "apply"))
    parser.add_argument("--pack", default=str(PACK))
    parser.add_argument("--yes", action="store_true")
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args(argv)
    pack = Path(args.pack).resolve()

    if args.command == "check":
        print(report(check(pack, offline=args.offline)))
        return 0
    if args.command == "trial":
        try:
            rows = trial(pack)
        except RuntimeError as error:
            print(f"trial: {error}", file=sys.stderr)
            return 1
        for name, code, message in rows:
            print(f"{'ok  ' if code == 0 else 'FAIL'} {name}: {message}")
        return 1 if any(code for _, code, _ in rows) else 0
    try:
        return apply(pack, packconfig.load(pack), args.yes)
    except packconfig.ConfigError as error:
        print(f"update: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
