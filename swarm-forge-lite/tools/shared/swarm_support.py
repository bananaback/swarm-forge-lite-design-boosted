#!/usr/bin/env python3
import json
import os
import subprocess
import sys
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
PACK = HERE.parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(PACK / "tools" / "refactorer"))

import harness
import record

_WORKSPACE = PACK.parent

class SwarmError(Exception):
    """A tool cannot act on the request."""


def _paths() -> harness.PathSet:
    """Resolve the wiring once, honouring the lane set in `main`."""
    return harness.load_path_set(None)


def _short(value) -> str:
    """A path relative to the workspace root when possible, to save bytes."""
    text = str(value)
    try:
        return str(Path(text).resolve().relative_to(_WORKSPACE))
    except (ValueError, OSError):
        return text


def _resolve_any(raw, paths: harness.PathSet | None = None) -> Path:
    """Resolve a relative path against the roots a caller is likely to mean."""
    path = Path(raw).expanduser()
    if path.is_absolute():
        return path
    bases: list[Path] = []
    if paths is not None:
        bases.append(Path(paths.workspace_root()))
    bases += [_WORKSPACE, PACK]
    for base in bases:
        candidate = base / raw
        if candidate.exists():
            return candidate
    return path


def _out_path(raw) -> Path:
    """Resolve an output path. The parent may not exist yet, so do not test it.

    A bare name is generated output: it belongs under the artifacts root, never at the
    workspace root or in a source tree.
    """
    path = Path(raw).expanduser()
    if path.is_absolute():
        return path
    if path.parent == Path("."):
        return _paths().artifacts_root() / path
    for base in [_WORKSPACE, PACK]:
        if (base / raw).parent.exists():
            return base / raw
    return _WORKSPACE / raw


def _run(argv, cwd=None, env=None):
    """Run a command and return (exit_code, stdout, stderr)."""
    merged = dict(os.environ)
    if env:
        merged.update(env)
    proc = subprocess.run(
        argv,
        cwd=str(cwd) if cwd else None,
        env=merged,
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.returncode, proc.stdout, proc.stderr


def _tool_env(paths: harness.PathSet) -> dict:
    """The environment a lane gives a test process, so a tool count equals a lane count.

    A role runs `<pack>/tools/shared/lane <subsystem> pytest ...` and gets
    `SWARM_TEST_DATA` plus the scoped caches. The `swarm` tools must give the
    same environment. Otherwise the tool and the role report different numbers
    for the same suite, and the role spends its time to reconcile them.
    """
    roots = [str(root.path.parent) for root in paths.persistent_roots()]
    for source in paths.source_roots():
        roots.append(str(Path(source).parent))
    existing = os.environ.get("PYTHONPATH", "")
    env = {
        "PYTHONPATH": os.pathsep.join([*roots, existing])
        if existing
        else os.pathsep.join(roots)
    }

    artifacts = paths.artifacts_root()
    scoped = {
        "SWARM_TEST_DATA": artifacts / "testdata",
        "PYTHONPYCACHEPREFIX": artifacts / "pycache",
        "TMPDIR": artifacts / "tmp",
        "HYPOTHESIS_STORAGE_DIRECTORY": artifacts / "hypothesis",
    }
    cache = artifacts / "pytest-cache"
    for path in [*scoped.values(), cache]:
        path.mkdir(parents=True, exist_ok=True)
    env.update({key: str(value) for key, value in scoped.items()})
    addopts = os.environ.get("PYTEST_ADDOPTS", "")
    env["PYTEST_ADDOPTS"] = f"-o cache_dir={cache} {addopts}".strip()
    lane = (os.environ.get("SWARM_LANE") or "").strip()
    if lane:
        env["SWARM_LANE"] = lane
    return env


def _counts(report: record.Report) -> tuple[int, int]:
    errors = sum(1 for f in report.findings if f.severity == record.ERROR)
    warnings = sum(1 for f in report.findings if f.severity == record.WARN)
    return errors, warnings


def _by_code(codes: list) -> dict:
    out: dict = {}
    for code in codes:
        key = code or "?"
        out[key] = out.get(key, 0) + 1
    return out


def _handle_dir(paths: harness.PathSet) -> Path:
    return paths.artifacts_root() / "handles"


def _save_handle(rows: list, paths: harness.PathSet, name: str) -> str:
    """Persist a full row set and return a short handle for `page`."""
    root = _handle_dir(paths)
    root.mkdir(parents=True, exist_ok=True)
    handle = uuid.uuid4().hex[:12]
    (root / f"{handle}.json").write_text(
        json.dumps({"name": name, "total": len(rows), "rows": rows}), encoding="utf-8"
    )
    return handle


def _load_handle(handle: str, paths: harness.PathSet) -> dict:
    path = _handle_dir(paths) / f"{handle}.json"
    if not path.exists():
        raise SwarmError(f"no such handle: {handle}")
    return json.loads(path.read_text(encoding="utf-8"))


