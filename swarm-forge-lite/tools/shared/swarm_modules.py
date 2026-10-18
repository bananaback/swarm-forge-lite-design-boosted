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


def _flat_interface(text: str) -> dict[str, str]:
    """Interface sections in a flat architecture.md, keyed by module id."""
    sections: dict[str, list[str]] = {}
    current = None
    for line in text.splitlines():
        if line.startswith("## "):
            title = line[3:].strip()
            if title.lower().startswith("interface "):
                current = title.split(None, 1)[1].strip()
                sections[current] = [line]
                continue
            current = None
        if current is not None:
            sections[current].append(line)
    return {name: "\n".join(lines).strip() + "\n" for name, lines in sections.items()}


def cmd_modules(args: dict) -> dict:
    """The module map and the module/interface layout of a subsystem."""
    subsystem = args.get("subsystem")
    if not subsystem:
        raise SwarmError("pass subsystem")
    root = PACK / "design" / "subsystems" / subsystem
    flat_arch = root / "architecture.md"
    arch = (
        flat_arch if flat_arch.is_file() else root / "02-architect" / "ARCHITECTURE.md"
    )
    ifc_dir = root / "interfaces"
    bnd_dir = root / "modules"
    interfaces = (
        sorted(p.stem for p in ifc_dir.glob("*.md")) if ifc_dir.is_dir() else []
    )
    if flat_arch.is_file():
        interfaces = sorted(_flat_interface(flat_arch.read_text(encoding="utf-8")))
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
        for child in sorted(p for p in bnd_dir.glob("*.md")):
            modules.append({"id": child.stem, "design": True, "skeleton": True})
    skeleton = root / "SKELETON.md"
    return {
        "subsystem": subsystem,
        "architecture": _short(arch) if arch.exists() else None,
        "interfaces": [
            {
                "id": i,
                "path": _short(
                    flat_arch if flat_arch.is_file() else ifc_dir / (i + ".md")
                ),
            }
            for i in interfaces
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
    root = PACK / "design" / "subsystems" / subsystem
    path = root / "interfaces" / f"{module}.md"
    if path.exists():
        return {
            "subsystem": subsystem,
            "module": module,
            "path": _short(path),
            "text": path.read_text(encoding="utf-8"),
        }
    flat = root / "architecture.md"
    if flat.is_file():
        sections = _flat_interface(flat.read_text(encoding="utf-8"))
        if module in sections:
            return {
                "subsystem": subsystem,
                "module": module,
                "path": _short(flat),
                "text": sections[module],
            }
    raise SwarmError(f"no such interface: {module} in {_short(root)}")


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
