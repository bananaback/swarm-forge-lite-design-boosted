#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PACK = HERE.parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(PACK / "tools" / "refactorer"))

from swarm_support import (
    SwarmError,
    _by_code,
    _paths,
    _run,
    _short,
    _tool_env,
)

_WORKSPACE = PACK.parent

_SUMMARY = re.compile(r"(\d+)\s+(passed|failed|error|errors|skipped|xfailed|xpassed)")


def _pytest_summary(out: str) -> dict:
    summary_line = None
    for line in reversed(out.splitlines()):
        if _SUMMARY.search(line) and (
            "passed" in line or "failed" in line or "error" in line
        ):
            summary_line = line.strip().strip("=").strip()
            break
    tallies: dict[str, int] = {}
    if summary_line:
        for count, word in _SUMMARY.findall(summary_line):
            key = "errors" if word in ("error", "errors") else word
            tallies[key] = tallies.get(key, 0) + int(count)
    failures = []
    seen: set[str] = set()
    for line in out.splitlines():
        match = re.match(r"^(FAILED|ERROR)\s+(\S+)(?:\s+-\s+(.*))?$", line)
        if match and match.group(2) not in seen:
            seen.add(match.group(2))
            failures.append(
                {"test": match.group(2), "reason": (match.group(3) or "").strip()[:200]}
            )
    return {"summary": summary_line, "tallies": tallies, "failures": failures}


def cmd_pytest(args: dict) -> dict:
    """Run pytest and return counts and failing tests, not the whole log."""
    paths = _paths()
    roots = paths.persistent_roots()
    if not roots:
        raise SwarmError("no persistent test root configured")
    selected = args.get("paths") or []
    full = args.get("scope") == "full" or (not selected and not args.get("k"))
    # A full run covers every configured root. A path-scoped run names paths in
    # one root, so it stays in the first root.
    runs = roots if not selected else roots[:1]
    tallies = {"passed": 0, "failed": 0, "errors": 0, "skipped": 0}
    failures = []
    summaries = []
    exits = []
    for entry in runs:
        persist = entry.path
        argv = [sys.executable, "-m", "pytest", "-q", "-rf", "--tb=line"]
        if args.get("k"):
            argv += ["-k", str(args["k"])]
        for raw in selected:
            candidate = Path(raw)
            argv.append(str(candidate if candidate.is_absolute() else persist / raw))
        code, out, _err = _run(argv, cwd=persist, env=_tool_env(paths))
        parsed = _pytest_summary(out)
        for key in tallies:
            tallies[key] += parsed["tallies"].get(key, 0)
        failures += parsed["failures"]
        if parsed["summary"]:
            summaries.append(parsed["summary"])
        exits.append(code)
    return {
        "tool": "pytest",
        "scope": "full" if full else "scoped",
        "roots": len(runs),
        **tallies,
        "failures": failures,
        "summary": "; ".join(summaries) or None,
        "exit": max(exits) if exits else 0,
        "ok": (max(exits) if exits else 0) == 0
        and tallies["failed"] == 0
        and tallies["errors"] == 0,
    }


def cmd_acceptance(args: dict) -> dict:
    """Run the acceptance pipeline for one feature or all features."""
    paths = _paths()
    roots = paths.persistent_roots()
    if not roots:
        raise SwarmError("no persistent test root configured")
    runs = [
        entry.path
        for entry in roots
        if (entry.path / "acceptance" / "run_acceptance.py").is_file()
    ]
    if not runs:
        raise SwarmError("no acceptance runner under the configured persistent roots")
    stems = []
    failures = []
    tallies = {"passed": 0, "failed": 0}
    summaries = []
    exits = []
    for tests_dir in runs:
        runner = tests_dir / "acceptance" / "run_acceptance.py"
        argv = [sys.executable, str(runner)]
        if args.get("feature") and args["feature"] != "*":
            argv.append(str(args["feature"]))
        code, out, _err = _run(argv, cwd=tests_dir, env=_tool_env(paths))
        stems += re.findall(r"^=== (\S+): parse ===$", out, re.MULTILINE)
        parsed = _pytest_summary(out)
        for key in tallies:
            tallies[key] += parsed["tallies"].get(key, 0)
        failures += parsed["failures"]
        if parsed["summary"]:
            summaries.append(parsed["summary"])
        exits.append(code)
    return {
        "tool": "run_acceptance",
        "features": stems,
        **tallies,
        "failures": failures,
        "summary": "; ".join(summaries) or None,
        "exit": max(exits) if exits else 0,
        "ok": (max(exits) if exits else 0) == 0 and tallies["failed"] == 0,
    }


def cmd_gherkin_parse(args: dict) -> dict:
    """Parse a .feature file to the JSON IR and summarize it."""
    paths = _paths()
    features = paths.features()
    if features is None or not features.is_configured():
        raise SwarmError("no features root configured")
    stem = args["feature"]
    feature = Path(stem)
    if not feature.is_absolute():
        feature = features.require() / f"{stem}.feature"
    if not feature.is_file():
        raise SwarmError(f"no such feature: {_short(feature)}")
    ir = paths.artifacts_root() / f"{feature.stem}.json"
    argv = [str(PACK / "tools" / "shared" / "gherkin-parser"), str(feature), str(ir)]
    code, _out, err = _run(argv)
    result = {"feature": _short(feature), "ir": _short(ir), "exit": code}
    if code == 0 and ir.exists():
        try:
            data = json.loads(ir.read_text(encoding="utf-8"))
            scenarios = [s.get("name") for s in data.get("scenarios", [])]
            result["scenario_count"] = len(scenarios)
            if args.get("names"):
                result["scenarios"] = scenarios
        except (json.JSONDecodeError, OSError):
            pass
    if err.strip():
        result["stderr"] = err.strip()[:300]
    return result


def _resolve_artifacts_path(raw: str, paths):
    """Find a path a caller named, under the artifacts root or the workspace root.

    `swarm.gherkinParse` returns a path relative to the workspace root and
    `swarm.gherkinDry` takes one relative to the artifacts root, so both resolve here
    and the two tools chain.
    """
    p = Path(raw)
    if p.is_absolute():
        return p if p.is_file() else None
    for base in (paths.artifacts_root(), _WORKSPACE, Path.cwd()):
        candidate = base / p
        if candidate.is_file():
            return candidate
    return None


def cmd_gherkin_dry(args: dict) -> dict:
    """Run the IR dry-checker and summarize the report.

    `ir` accepts the name under the artifacts root, or any path that resolves: the
    `swarm.gherkinParse` result passes straight through.
    """
    paths = _paths()
    ir = _resolve_artifacts_path(args["ir"], paths)
    if ir is None:
        raise SwarmError(f"no such IR: {_short(paths.artifacts_root() / args['ir'])}")
    report_path = ir.with_suffix(".dry.json")
    argv = [str(PACK / "tools" / "specifier" / "ir-dry-checker")]
    if args.get("includeExact"):
        argv.append("--include-exact")
    argv += [str(ir), str(report_path)]
    code, _out, _err = _run(argv)
    result = {"ir": _short(ir), "exit": code}
    if code == 0 and report_path.exists():
        try:
            data = json.loads(report_path.read_text(encoding="utf-8"))
            findings = data.get("findings") or data.get("checks") or []
            result["counts"] = _by_code(
                [f.get("kind") or f.get("rule") for f in findings]
            )
            result["total"] = len(findings)
            if args.get("view") in ("rows", "full") or args.get("full"):
                limit = int(args.get("limit", 10))
                result["findings"] = findings[:limit]
                result["truncated"] = len(findings) > limit
        except (json.JSONDecodeError, OSError):
            pass
    return result
