#!/usr/bin/env python3


def _tool(
    name, group, replaces, summary, params, returns, example, output, notes="", roles=""
):
    """One tool's help entry. `params` is a list of (name, type, default, desc)."""
    return {
        "name": name,
        "group": group,
        "replaces": replaces,
        "roles": roles,
        "summary": summary,
        "params": [
            {"name": n, "type": t, "default": d, "desc": desc}
            for n, t, d, desc in params
        ],
        "returns": returns,
        "example": example,
        "output": output,
        "notes": notes,
    }


_M = (
    "subsystem",
    "string",
    "-",
    "The lane. Sets SWARM_LANE; the same string as the record id.",
)


_R = (
    "role",
    "string",
    "-",
    "interrogator | architect | designer | critic | specifier | coder | test-reviewer | refactorer | hotfixer.",
)


_VIEW = (
    "view",
    "summary|rows|all",
    "summary",
    "summary = counts. rows = inline cols+rows (limit). all = a paging handle.",
)


_LIMIT = ("limit", "int", "50", "Max rows when view is rows.")


_UML_OPS_HELP = None


def _uml_ops_help() -> dict | None:
    """The uml op catalog, read from the tool so the help never drifts."""
    global _UML_OPS_HELP
    if _UML_OPS_HELP is None:
        try:
            from umlmodel.ops import entry

            _UML_OPS_HELP = entry()
        except Exception:  # noqa: BLE001  # the catalog must not break over one tool's help
            _UML_OPS_HELP = {}
    return _UML_OPS_HELP or None


def _with_uml_help(tool: dict) -> dict:
    """Add the per-op usage to the uml tool's help entry."""
    entry = _uml_ops_help()
    if entry:
        tool["ops"] = entry["ops"]
        tool["invariants"] = entry["invariants"]
    return tool


