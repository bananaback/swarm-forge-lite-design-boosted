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
)

_WORKSPACE = PACK.parent

def cmd_docs(args: dict) -> dict:
    """The compact catalog: every tool with a summary and one example."""
    from swarm_json import TOOLS
    return {
        "pack": str(PACK),
        "backend": str(Path(__file__).resolve()),
        "backend_call": "python3 <pack>/tools/shared/swarm_json.py <command> '<json-args>'",
        "views": "List tools default to a summary. view:'rows' = inline cols+rows. view:'all' = a paging handle.",
        "next": "call swarm.help({tool:'ruff'}) for one tool's params and output",
        "tools": [
            {
                "command": t["name"],
                "group": t["group"],
                "summary": t["summary"],
                "example": t["example"],
            }
            for t in TOOLS
        ],
    }


def cmd_help(args: dict) -> dict:
    """One tool's full help. With no tool, the whole catalog."""
    from swarm_json import BY_NAME, TOOLS
    name = args.get("tool") or args.get("name")
    if not name:
        return {
            "tools": [
                {
                    "name": t["name"],
                    "group": t["group"],
                    "replaces": t["replaces"],
                    "summary": t["summary"],
                }
                for t in TOOLS
            ],
            "hint": "call swarm.help({tool:'ruff'}) for one tool",
        }
    tool = BY_NAME.get(name)
    if tool is None:
        raise SwarmError(f"no tool {name!r}; known: {sorted(BY_NAME)}")
    return tool


def _help_text(name: str | None = None) -> str:
    """A plain-text usage page, for `python3 swarm_json.py --help`."""
    from swarm_json import BY_NAME, TOOLS
    if name is None:
        lines = [
            "swarm_json -- the backend of the swarm.* Code Mode tools",
            "",
            "usage:",
            "  python3 swarm_json.py <command> '<json-args>'",
            "  python3 swarm_json.py <command> --help",
            "  python3 swarm_json.py --help",
            "",
            "The args JSON may carry subsystem=<name> to set the lane.",
        ]
        for group in _GROUPS:
            members = [t for t in TOOLS if t["group"] == group]
            if not members:
                continue
            lines.append("")
            lines.append(f"[{group}]")
            for t in members:
                lines.append(f"  {t['name']:<14} {t['summary']}")
        lines += [
            "",
            "The same catalog is `swarm.docs()` in Code Mode; one tool's detail is `swarm.help({tool})`.",
        ]
        return "\n".join(lines)
    tool = BY_NAME.get(name)
    if tool is None:
        return f"swarm_json: no tool {name!r}; known: {', '.join(sorted(BY_NAME))}"
    lines = [
        f"{tool['name']} -- {tool['summary']}",
        f"group: {tool['group']}    replaces: {tool['replaces']}    roles: {tool['roles'] or '-'}",
        "",
        "params:",
    ]
    if tool["params"]:
        for param in tool["params"]:
            lines.append(
                f"  {param['name']:<10} {param['type']:<22} default={param['default']:<26} {param['desc']}"
            )
    else:
        lines.append("  (none)")
    lines += [
        "",
        f"returns: {tool['returns']}",
        f"example: {tool['example']}",
        f"output:  {json.dumps(tool['output'], default=str)}",
    ]
    if tool["notes"]:
        lines.append(f"notes:   {tool['notes']}")
    if tool.get("ops"):
        lines += ["", f"ops ({len(tool['ops'])}):"]
        for item in tool["ops"]:
            params = ", ".join(param["name"] for param in item["params"]) or "-"
            lines.append(f"  {item['op']:<16} {item['kind']:<6} {item['purpose']}")
            lines.append(f"      params: {params}")
            lines.append(f"      e.g. {item['example']}")
        lines += ["", "invariants:"]
        lines += [f"  - {line}" for line in tool.get("invariants", [])]
    return "\n".join(lines)


_GROUPS = [
    "resolve",
    "method",
    "record",
    "quality",
    "gherkin",
    "uml",
    "aggregate",
    "meta",
]


