#!/usr/bin/env python3
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PACK = HERE.parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(PACK / "tools" / "refactorer"))

from swarm_support import (
    SwarmError,
    _short,
)

_WORKSPACE = PACK.parent

def cmd_modules(args: dict) -> dict:
    """The module map and the module/interface layout of a subsystem."""
    subsystem = args.get("subsystem")
    if not subsystem:
        raise SwarmError("pass subsystem")
    root = PACK / "design" / "subsystems" / subsystem
    arch = root / "02-architect" / "ARCHITECTURE.md"
    ifc_dir = root / "interfaces"
    bnd_dir = root / "modules"
    interfaces = (
        sorted(p.stem for p in ifc_dir.glob("*.md")) if ifc_dir.is_dir() else []
    )
    modules = []
    if bnd_dir.is_dir():
        for child in sorted(p for p in bnd_dir.iterdir() if p.is_dir()):
            modules.append(
                {
                    "id": child.name,
                    "design": (child / "DESIGN.md").exists(),
                    "skeleton": (child / "SKELETON.md").exists(),
                }
            )
    skeleton = root / "SKELETON.md"
    return {
        "subsystem": subsystem,
        "architecture": _short(arch) if arch.exists() else None,
        "interfaces": [
            {"id": i, "path": _short(ifc_dir / (i + ".md"))} for i in interfaces
        ],
        "modules": modules,
        "split_ready": arch.exists() and len(interfaces) > 0,
        "subsystem_skeleton": _short(skeleton) if skeleton.exists() else None,
    }


def cmd_interface(args: dict) -> dict:
    """The frozen interface text of one module."""
    subsystem = args.get("subsystem")
    if not subsystem:
        raise SwarmError("pass subsystem")
    module = args.get("module")
    if not module:
        raise SwarmError("pass module")
    path = PACK / "design" / "subsystems" / subsystem / "interfaces" / f"{module}.md"
    if not path.exists():
        raise SwarmError(f"no such interface: {_short(path)}")
    return {
        "subsystem": subsystem,
        "module": module,
        "path": _short(path),
        "text": path.read_text(encoding="utf-8"),
    }


def cmd_goal(args: dict) -> dict:
    """Read, or write, the orchestrator's scratchpad for a subsystem."""
    subsystem = args.get("subsystem")
    if not subsystem:
        raise SwarmError("pass subsystem")
    path = PACK / "design" / "subsystems" / subsystem / "GOAL.md"
    text = args.get("text")
    if text is not None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(str(text), encoding="utf-8")
    exists = path.exists()
    return {
        "subsystem": subsystem,
        "path": _short(path),
        "exists": exists,
        "text": path.read_text(encoding="utf-8") if exists else None,
    }


