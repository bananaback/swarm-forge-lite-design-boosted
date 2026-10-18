#!/usr/bin/env python3
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PACK = HERE.parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(PACK / "tools" / "refactorer"))

from swarm_support import (
    SwarmError,
    _load_handle,
    _out_path,
    _paths,
    _resolve_any,
    _run,
    _short,
)

_WORKSPACE = PACK.parent


def _resolve_model(raw: str, subsystem: str | None) -> Path:
    path = Path(raw)
    if path.is_absolute():
        return path
    if subsystem:
        return PACK / "design" / "subsystems" / subsystem / raw
    return path


def cmd_uml_render(args: dict) -> dict:
    """Render model.json to a standalone model.html."""
    model = _resolve_model(args.get("model") or "model.json", args.get("subsystem"))
    argv = [
        sys.executable,
        str(PACK / "tools" / "shared" / "umlview" / "render.py"),
        str(model),
    ]
    if args.get("out"):
        argv += ["--out", str(_out_path(args["out"]))]
    if args.get("check"):
        argv.append("--check")
    code, out, err = _run(argv)
    return {
        "tool": "umlview-render",
        "model": _short(model),
        "exit": code,
        "stdout": out.strip() or None,
        "stderr": err.strip() or None,
    }


def _lane_from_model(model: Path) -> str | None:
    """The subsystem whose design tree holds the model, if any."""
    base = PACK / "design" / "subsystems"
    try:
        parts = model.resolve().relative_to(base.resolve()).parts
    except (ValueError, OSError):
        return None
    return parts[0] if parts else None


def _default_report(paths, model: Path) -> Path:
    """The lane's CRAP report; a model under design/subsystems names the lane."""
    lane = _lane_from_model(model)
    if lane:
        return PACK / "dump" / lane / ".metrics" / "crap.txt"
    return paths.artifacts_root() / ".metrics" / "crap.txt"


def cmd_uml_sync(args: dict) -> dict:
    """Overlay the real signatures and CRAP metrics onto the model."""
    model = _resolve_model(args.get("model") or "model.json", args.get("subsystem"))
    paths = _paths()
    if args.get("crap"):
        report = _resolve_any(args["crap"], paths)
        warning = None
    else:
        report = _default_report(paths, model)
        if not report.is_file():
            return {
                "tool": "umlview-sync",
                "model": _short(model),
                "exit": 2,
                "ok": False,
                "stderr": (
                    f"sync: no CRAP report at {report}; "
                    "run swarm.crap first or pass crap=<path>"
                ),
            }
        warning = f"sync: using default CRAP report {report}"
    argv = [
        sys.executable,
        str(PACK / "tools" / "shared" / "umlview" / "sync_python.py"),
        str(model),
        "--source",
        str(
            _resolve_any(args["source"], paths)
            if args.get("source")
            else (paths.source_roots()[0] if paths.source_roots() else ".")
        ),
        "--crap",
        str(report),
    ]
    # Overlay model.json itself. One topology, one review page. No model.live copy.
    out_path = _out_path(args["out"]) if args.get("out") else model
    argv += ["--out", str(out_path)]
    code, out, err = _run(argv)
    result = {
        "tool": "umlview-sync",
        "model": _short(model),
        "exit": code,
        "stdout": out.strip() or None,
        "stderr": err.strip() or None,
    }
    if warning:
        result["warn"] = warning
    return result


def cmd_uml_scan(args: dict) -> dict:
    """Scan a Python source root into a model.json.

    The output lands under the artifacts root by default. The scanned root is the
    SOURCE tree, and a generated model must never be written into it.
    """
    paths = _paths()
    root = _resolve_any(args["root"], paths)
    argv = [
        sys.executable,
        str(PACK / "tools" / "shared" / "umlview" / "scan_python.py"),
        str(root),
    ]
    for key in ("prefix", "title"):
        if args.get(key):
            argv += [f"--{key}", str(args[key])]
    out = (
        _out_path(args["out"])
        if args.get("out")
        else paths.artifacts_root() / "model.scan.json"
    )
    argv += ["--out", str(out)]
    code, out, err = _run(argv)
    return {
        "tool": "umlview-scan",
        "root": _short(root),
        "exit": code,
        "stdout": out.strip() or None,
        "stderr": err.strip() or None,
    }


def _uml_model_path(raw, subsystem) -> Path:
    """Resolve a model path: absolute, subsystem-relative, pack, then workspace."""
    path = Path(raw).expanduser()
    if path.is_absolute():
        return path
    candidates = []
    if subsystem:
        candidates.append(PACK / "design" / "subsystems" / str(subsystem) / raw)
    candidates += [PACK / raw, _WORKSPACE / raw, Path.cwd() / raw]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return PACK / raw


def cmd_uml(args: dict) -> dict:
    """Query or mutate a uml model.json through the umlmodel tool.

    One op per call. The tool loads, validates, applies the op, validates again,
    then writes atomically. `swarm.help({tool:'uml'})` lists every op.
    """
    op = args.get("op")
    if not op:
        raise SwarmError("pass op; run op:'list' for every op")
    if op == "render":
        return cmd_uml_render(args)
    if op == "sync":
        return cmd_uml_sync(args)
    if op == "scan":
        return cmd_uml_scan(args)
    argv = [
        sys.executable,
        str(PACK / "tools" / "shared" / "umlmodel"),
        str(op),
        "--json",
    ]
    if args.get("model"):
        argv += ["--model", str(_uml_model_path(args["model"], args.get("subsystem")))]
    if args.get("dryRun"):
        argv.append("--dry-run")
    control = {"op", "model", "subsystem", "dryRun", "view", "limit"}
    payload = {key: value for key, value in args.items() if key not in control}
    if payload:
        argv += ["--args", json.dumps(payload)]
    code, out, err = _run(argv)
    result: dict = {}
    if out.strip():
        try:
            parsed = json.loads(out)
            if isinstance(parsed, dict):
                result = parsed
        except json.JSONDecodeError:
            result = {}
    if not result:
        return {
            "tool": "umlmodel",
            "model": args.get("model"),
            "op": op,
            "ok": False,
            "changed": False,
            "exit": code,
            "stdout": out.strip()[:500] or None,
            "error": (err.strip() or "umlmodel printed no JSON")[:500],
        }
    result.setdefault("tool", "umlmodel")
    result["exit"] = code
    if err.strip() and not result.get("message"):
        result["stderr"] = err.strip()[:500]
    return result


def cmd_page(args: dict) -> dict:
    """Fetch a page of a saved handle (from a view:"all" call)."""
    paths = _paths()
    data = _load_handle(args["handle"], paths)
    rows = data["rows"]
    total = len(rows)
    offset = max(0, int(args.get("offset", 0)))
    limit = int(args.get("limit", 50))
    page = rows[offset : offset + limit] if limit > 0 else rows[offset:]
    return {
        "handle": args["handle"],
        "name": data.get("name"),
        "total": total,
        "offset": offset,
        "returned": len(page),
        "next": offset + len(page) if offset + len(page) < total else None,
        "items": page,
    }
