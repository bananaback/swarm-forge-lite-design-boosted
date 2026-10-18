#!/usr/bin/env python3
import json
import os
import re
import shlex
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PACK = HERE.parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(PACK / "tools" / "refactorer"))

import harness
from swarm_support import (
    _by_code,
    _paths,
    _resolve_any,
    _run,
    _save_handle,
    _short,
    _tool_env,
)

_WORKSPACE = PACK.parent


def cmd_ruff(args: dict) -> dict:
    """Structured ruff findings, without the annotated source frames.

    Default: the count and the by-code tally. view:"rows" or "all" adds the rows.
    """
    paths = _paths()
    originals = args.get("paths") or []
    resolved = [str(_resolve_any(raw, paths)) for raw in originals]
    if not resolved:
        resolved = [str(p) for p in paths.source_roots()] + [
            str(root.path) for root in paths.persistent_roots()
        ]
    wrapper = PACK / "tools" / "shared" / "ruff4py"
    code, out, err = _run(
        [sys.executable, str(wrapper), "--output-format", "json", *resolved]
    )
    try:
        data = json.loads(out) if out.strip() else []
    except json.JSONDecodeError:
        return {
            "tool": "ruff",
            "error": "ruff did not return JSON",
            "stderr": err.strip()[:500],
            "exit": code,
        }
    rows = []
    for item in data:
        location = item.get("location") or {}
        rows.append(
            [
                item.get("code"),
                _short(item.get("filename", "")),
                location.get("row"),
                location.get("column"),
                item.get("message"),
                (item.get("fix") or {}).get("applicability"),
            ]
        )
    result = {
        "tool": "ruff",
        "total": len(rows),
        "byCode": _by_code([r[0] for r in rows]),
        "exit": code,
        "ok": code == 0 and not rows,
    }
    view = args.get("view", "summary")
    if view in ("rows", "full"):
        limit = int(args.get("limit", 50))
        result["cols"] = RUFF_COLS
        result["rows"] = rows[:limit]
        if len(rows) > limit:
            result["truncated"] = True
            result["handle"] = _save_handle(rows, paths, "ruff")
    elif view == "all":
        result["handle"] = _save_handle(rows, paths, "ruff")
        result["note"] = "fetch more rows with swarm.page({handle})"
    return result


def cmd_format(args: dict) -> dict:
    """Files `ruff format --check` would rewrite. Default: the count.

    Ruff discovers the repository config from each file's own directory. The
    cache stays under the artifacts root, so nothing lands in the project tree.
    """
    paths = _paths()
    originals = args.get("paths") or []
    resolved = [str(_resolve_any(raw, paths)) for raw in originals]
    if not resolved:
        resolved = [str(p) for p in paths.source_roots()] + [
            str(root.path) for root in paths.persistent_roots()
        ]
    cache = paths.artifacts_root() / "ruff-cache"
    argv = [
        sys.executable,
        "-m",
        "ruff",
        "format",
        "--check",
        "--cache-dir",
        str(cache),
        *resolved,
    ]
    code, out, err = _run(argv)
    match = re.search(r"(\d+) files? would be reformatted", out)
    count = int(match.group(1)) if match else 0
    result = {
        "tool": "ruff-format",
        "total": count,
        "exit": code,
        "ok": code == 0 and count == 0,
    }
    if err.strip():
        result["stderr"] = err.strip()[:300]
    return result


def _dry_pairs(output: str) -> list:
    """The duplicate pairs of a dryer report, one [first, second] per block."""
    pairs = []
    for block in re.split(r"\n\s*\n", output.strip()):
        pos = re.findall(r"^\s*(.+?):(\d+)-(\d+)\s*$", block, re.MULTILINE)
        if len(pos) == 2:
            pairs.append(
                [
                    f"{_short(pos[0][0])}:{pos[0][1]}-{pos[0][2]}",
                    f"{_short(pos[1][0])}:{pos[1][1]}-{pos[1][2]}",
                ]
            )
    return pairs


def _dry_env(paths: harness.PathSet) -> dict:
    """The lane environment plus the vendored dryer package on PYTHONPATH."""
    env = _tool_env(paths)
    tools = str(PACK / "tools" / "shared")
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = os.pathsep.join([tools, existing]) if existing else tools
    return env


def _dry_argv(paths: harness.PathSet, args: dict) -> list:
    """The vendored dryer command, at the pack's DRY settings.

    `--root` is the artifacts root, so the `.metrics/dry.edn` snapshot lands
    under `dump/` and never in the source tree.
    """
    return [
        sys.executable,
        "-m",
        DRY_NAME,
        "--root",
        str(paths.artifacts_root()),
        "--threshold",
        str(args.get("threshold", DRY_THRESHOLD)),
        "--min-lines",
        str(args.get("minLines", DRY_MIN_LINES)),
        "--min-nodes",
        str(args.get("minNodes", DRY_MIN_NODES)),
    ]


def cmd_dry(args: dict) -> dict:
    """Duplicate-code pairs. Default: the count. view:"rows" adds the pairs."""
    paths = _paths()
    originals = args.get("paths") or [str(p) for p in paths.source_roots()]
    resolved = [str(_resolve_any(raw, paths)) for raw in originals]
    argv = _dry_argv(paths, args) + resolved
    code, out, err = _run(argv, env=_dry_env(paths))
    pairs = _dry_pairs(out)
    result = {
        "tool": DRY_NAME,
        "total": len(pairs),
        "exit": code,
        "ok": code == 0 and not pairs,
    }
    view = args.get("view", "summary")
    if view in ("rows", "full"):
        limit = int(args.get("limit", 50))
        result["pairs"] = pairs[:limit]
        if len(pairs) > limit:
            result["truncated"] = True
            result["handle"] = _save_handle(pairs, paths, "dry")
    elif view == "all":
        result["handle"] = _save_handle(pairs, paths, "dry")
    if err.strip():
        result["stderr"] = err.strip()[:300]
    return result


def _crap_value(text: str) -> float | None:
    try:
        return float(text)
    except ValueError:
        return None


def _crap_rows(output: str) -> list:
    """The report rows of a crapper run, worst first."""
    rows = []
    for line in output.splitlines():
        match = _CRAP_ROW.match(line)
        if not match:
            continue
        rows.append(
            {
                "function": match.group("fn").strip(),
                "namespace": match.group("ns"),
                "cc": int(match.group("cc")),
                "coverage": match.group("cov"),
                "crap": match.group("crap"),
            }
        )
    return rows


def _crap_over(rows: list) -> list:
    """The rows whose CRAP score is above the pack's threshold."""
    return [row for row in rows if (_crap_value(row["crap"]) or 0.0) > CRAP_THRESHOLD]


def _newest_python_mtime(roots) -> float:
    """The newest mtime of a .py file under the given roots."""
    newest = 0.0
    skip = {"__pycache__", ".pytest_cache", ".hypothesis", ".git", ".ruff_cache"}
    for raw in roots:
        base = Path(raw)
        if not base.exists():
            continue
        candidates = base.rglob("*.py") if base.is_dir() else [base]
        for path in candidates:
            if any(part in skip for part in path.parts):
                continue
            try:
                newest = max(newest, path.stat().st_mtime)
            except OSError:
                continue
    return newest


def _crap_report(root: Path) -> Path:
    """Where the pack's coverage run writes the report crapper reads."""
    return root / "target" / "coverage" / "python" / "lcov.info"


def _crap_coverage_fresh(paths, root: Path, sources) -> bool:
    """True when the coverage report is newer than every source and test file."""
    report = _crap_report(root)
    if not report.exists():
        return False
    watched = list(sources) + [str(entry.path) for entry in paths.persistent_roots()]
    newest = _newest_python_mtime(watched)
    return newest > 0.0 and report.stat().st_mtime >= newest


def _crap_coverage_command(paths, root: Path) -> str:
    """The coverage.py command that writes the report crapper reads.

    crapper runs it in a shell, in the artifacts root. The ';' keeps the lcov
    report even when the tests fail, so the run reports the coverage it did get.
    """
    data = _crap_report(root).parent / ".coverage"
    tests = [str(entry.path) for entry in paths.persistent_roots()]
    run = [
        sys.executable,
        "-m",
        "coverage",
        "run",
        f"--data-file={data}",
        "-m",
        "pytest",
        *tests,
    ]
    lcov = [
        sys.executable,
        "-m",
        "coverage",
        "lcov",
        f"--data-file={data}",
        "-o",
        str(_crap_report(root)),
    ]
    return " ; ".join(
        " ".join(shlex.quote(part) for part in cmd) for cmd in (run, lcov)
    )


def _crap_env(paths) -> dict:
    """The lane environment plus the vendored crapper package on PYTHONPATH."""
    env = _tool_env(paths)
    tools = str(PACK / "tools" / "refactorer")
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = os.pathsep.join([tools, existing]) if existing else tools
    return env


def _crap_argv(paths, args) -> list:
    """The vendored crapper command, at the pack's CRAP 10 threshold."""
    root = paths.artifacts_root()
    sources = args.get("sourceRoot") or [str(p) for p in paths.source_roots()]
    argv = [
        sys.executable,
        "-m",
        CRAP_NAME,
        "--root",
        str(root),
        "--threshold",
        f"{CRAP_THRESHOLD:.0f}",
    ]
    for source in sources:
        argv += ["--source-root", str(source)]
    reuse = args.get("useExisting") or (
        args.get("reuseFresh") and _crap_coverage_fresh(paths, root, sources)
    )
    if reuse:
        argv.append("--use-existing-coverage")
    else:
        _crap_report(root).parent.mkdir(parents=True, exist_ok=True)
        argv += ["--coverage-command", _crap_coverage_command(paths, root)]
    argv += list(args.get("filters") or [])
    return argv


def cmd_crap(args: dict) -> dict:
    """CRAP (complexity x coverage). Default: only the rows above the threshold."""
    paths = _paths()
    code, out, err = _run(_crap_argv(paths, args), env=_crap_env(paths))
    rows = _crap_rows(out)
    result = {
        "tool": CRAP_NAME,
        "threshold": CRAP_THRESHOLD,
        "total": len(rows),
        "above": len(_crap_over(rows)),
        "rows": rows if args.get("all") else _crap_over(rows),
        "exit": code,
        "ok": code == 0 and not _crap_over(rows),
    }
    if err.strip():
        result["stderr"] = err.strip()[:300]
    return result


DRY_NAME = "dryer"


DRY_THRESHOLD = "0.82"


DRY_MIN_LINES = 4


DRY_MIN_NODES = 20


CRAP_THRESHOLD = 10.0


CRAP_NAME = "crapper"


_CRAP_ROW = re.compile(
    r"^(?P<fn>.*?)\s+(?P<ns>\S+)\s+(?P<cc>\d+)\s+(?P<cov>\S+)\s+(?P<crap>\S+)\s*$"
)


RUFF_COLS = ["code", "file", "line", "col", "message", "fix_applicability"]
