#!/usr/bin/env python3
"""Check that this install is healthy and that a project is ready to work.

    python3 tools/doctor.py                 # the selected project
    python3 tools/doctor.py --project <p>
    python3 tools/doctor.py --json

Every line is `ok`, `warn` or `fail` plus the remedy. Exit 1 when anything
failed; warnings never fail. This is the first command of a dispatch and the
last check of an install.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

PACK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACK / "tools" / "shared"))

import packconfig  # noqa: E402
import packschema  # noqa: E402


def _row(status: str, text: str) -> tuple[str, str]:
    return status, text


def _capabilities(entry: dict) -> list[tuple[str, str]]:
    rows = []
    wanted = entry.get("capabilities")
    if wanted is None:
        wanted = {"gherkin": True, "duplication": True, "crap": True}
    for capability, enabled in wanted.items():
        if not enabled:
            rows.append(_row("ok", f"capability {capability}: disabled"))
            continue
        if capability == "gherkin":
            found = shutil.which("bb") is not None
            rows.append(_row("ok" if found else "warn",
                             f"capability {capability}: {'bb found' if found else 'bb not on PATH'}"))
        elif capability in {"duplication", "crap"}:
            module = "tree_sitter_language_pack"
            if capability == "crap":
                module = "coverage"
            found = importlib.util.find_spec(module) is not None
            rows.append(_row("ok" if found else "warn",
                             f"capability {capability}: {module} {'available' if found else 'missing'}"))
        else:
            rows.append(_row("warn", f"capability {capability}: unknown capability"))
    return rows


def _git(pack: Path) -> list[tuple[str, str]]:
    if not (pack / ".git").exists():
        return [_row("warn", "git: this pack is not a checkout; update checks skipped")]
    status = subprocess.run(
        ["git", "-C", str(pack), "status", "--porcelain"],
        capture_output=True, text=True, check=False,
    )
    rows = []
    if status.returncode != 0:
        rows.append(_row("warn", "git: status unreadable"))
    else:
        dirty = [line for line in status.stdout.splitlines() if not line.startswith("??")]
        if dirty:
            rows.append(_row("warn", f"git: {len(dirty)} modified harness file(s); upstream them"))
    counts = subprocess.run(
        ["git", "-C", str(pack), "rev-list", "--left-right", "--count", "@{u}...HEAD"],
        capture_output=True, text=True, check=False,
    )
    if counts.returncode == 0:
        behind, ahead = counts.stdout.split()
        if int(behind):
            rows.append(_row("warn", f"git: {behind} commit(s) behind origin; run tools/update.py check"))
        if int(ahead):
            rows.append(_row("ok", f"git: {ahead} local commit(s) not pushed"))
    return rows


def _project_rows(pack: Path, entry: dict, name: str) -> list[tuple[str, str]]:
    rows = []
    project = (pack / entry["project_root"]).resolve()
    if not project.is_dir():
        return [_row("fail", f"project tree missing: {project} — fix project_root")]
    rows.append(_row("ok", f"project tree: {project}"))

    for root in entry.get("source_roots", []):
        path = (project / root).resolve()
        rows.append(_row("ok" if path.exists() else "fail",
                         f"source root: {path}"))
    class_root = entry.get("class_root")
    if class_root:
        path = (project / class_root).resolve()
        rows.append(_row("ok" if path.is_dir() else "fail", f"class root: {path}"))
    docs = (project / entry.get("docs_root", "docs")).resolve()
    rows.append(_row("ok" if docs.is_dir() else "fail", f"docs root: {docs}"))

    design_root = entry.get("design_root")
    if design_root:
        design = (project / design_root).resolve()
        rows.append(_row("ok" if design.is_dir() else "fail", f"design folder: {design}"))
        for name in ("runtime.json", "overlay.json"):
            path = design / name
            rows.append(_row("ok" if path.is_file() else "fail", f"design file: {path}"))
        policy = design / "policy.json"
        rows.append(_row("ok" if policy.is_file() else "warn", f"design policy: {policy}"))
    else:
        legacy = pack / "architecture" / name
        rows.append(_row("warn", f"design: legacy pack path ({legacy.parent}); set design_root"))

    specs = entry.get("specs") or {}
    if not specs:
        rows.append(_row("fail", "specs: none declared — docs validate cannot pass"))
    for filename in specs:
        path = docs / "specs" / filename
        rows.append(_row("ok" if path.is_file() else "fail", f"spec: {path}"))

    for label, key in (("unit path", "unit_paths"), ("features", "features")):
        value = entry.get(key)
        if value:
            path = (project / value).resolve()
            rows.append(_row("ok" if path.exists() else "warn", f"{label}: {path}"))
    if not entry.get("acceptance_command"):
        rows.append(_row("warn", "acceptance: no command configured"))
    return rows


def run(pack: Path, config: dict, name: str) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    try:
        rows.append(_row("ok", f"config: {packconfig.config_path(pack)}"))
    except packconfig.ConfigError as error:
        return [_row("fail", str(error))]

    errors, warnings = packschema.validate(config, packschema.load(pack))
    rows.extend(_row("fail", f"schema: {problem}") for problem in errors)
    rows.extend(_row("warn", f"schema: {problem}") for problem in warnings)
    if not errors:
        rows.append(_row("ok", "schema: valid"))

    project_md = pack / "PROJECT.md"
    if not project_md.is_file():
        rows.append(_row("warn", "PROJECT.md: missing — copy PROJECT.md.example"))
    elif "## Environment" not in project_md.read_text(encoding="utf-8"):
        rows.append(_row("warn", "PROJECT.md: no ## Environment section"))
    else:
        rows.append(_row("ok", f"PROJECT.md: {project_md}"))

    entry = config["projects"][name]
    rows.extend(_capabilities(entry))
    rows.extend(_project_rows(pack, entry, name))
    rows.extend(_git(pack))
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", default="", help="project name; default: PACK_PROJECT")
    parser.add_argument("--json", action="store_true", help="machine-readable rows")
    args = parser.parse_args(argv)

    try:
        config = packconfig.load(PACK)
        if args.project:
            import os
            os.environ["PACK_PROJECT"] = args.project
        name, _ = packconfig.select(config)
    except packconfig.ConfigError as error:
        print(f"doctor: {error}", file=sys.stderr)
        return 1

    rows = run(PACK, config, name)
    if args.json:
        print(json.dumps([{"status": s, "text": t} for s, t in rows], indent=2))
    else:
        for status, text in rows:
            print(f"{status:4} {text}")
        failures = sum(1 for status, _ in rows if status == "fail")
        warnings = sum(1 for status, _ in rows if status == "warn")
        print(f"\n{len(rows)} checks, {failures} failed, {warnings} warnings")
    return 1 if any(status == "fail" for status, _ in rows) else 0


if __name__ == "__main__":
    raise SystemExit(main())
