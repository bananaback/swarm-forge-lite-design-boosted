#!/usr/bin/env python3
"""swarm_json -- the machine-readable backend for the `swarm.*` Code Mode tools.

Thin facade: imports the domain siblings, builds the tool catalog, and runs the CLI.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PACK = HERE.parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(PACK / "tools" / "refactorer"))

import harness  # noqa: F401
import questions  # noqa: F401
import record  # noqa: F401
from swarm_catalog_core import CORE_TOOLS
from swarm_catalog_gate import GATE_TOOLS
from swarm_catalog_modules import MODULES_TOOLS
from swarm_catalog_quality import QUALITY_TOOLS
from swarm_catalog_support import (  # noqa: F401
    _LIMIT,
    _M,
    _R,
    _UML_OPS_HELP,
    _VIEW,
    _tool,
    _uml_ops_help,
    _with_uml_help,
)
from swarm_catalog_test import TEST_TOOLS
from swarm_catalog_uml import UML_TOOLS
from swarm_core import (  # noqa: F401
    FINDING_COLS,
    _envelope_text,
    _form_index,
    _form_items,
    _report_rows,
    _report_summary,
    cmd_check,
    cmd_check_envelope,
    cmd_clean,
    cmd_decisions,
    cmd_envelope,
    cmd_gen_doc,
    cmd_guide,
    cmd_init_work,
    cmd_lint_record,
    cmd_status,
    cmd_vocab_rename,
)
from swarm_gate import (  # noqa: F401
    _checked,
    _write_union_skeleton,
    cmd_doctor,
    cmd_gate,
    cmd_gen_record,
    cmd_ready,
    cmd_report,
)
from swarm_help import (  # noqa: F401
    _GROUPS,
    _help_text,
    cmd_docs,
    cmd_help,
)
from swarm_modules import (
    cmd_goal,
    cmd_interface,
    cmd_modules,
)
from swarm_quality import (  # noqa: F401
    _CRAP_ROW,
    CRAP_NAME,
    CRAP_THRESHOLD,
    DRY_MIN_LINES,
    DRY_MIN_NODES,
    DRY_NAME,
    DRY_THRESHOLD,
    RUFF_COLS,
    _crap_argv,
    _crap_coverage_command,
    _crap_coverage_fresh,
    _crap_env,
    _crap_over,
    _crap_report,
    _crap_rows,
    _crap_value,
    _dry_argv,
    _dry_env,
    _dry_pairs,
    _newest_python_mtime,
    cmd_crap,
    cmd_dry,
    cmd_format,
    cmd_ruff,
)
from swarm_support import (  # noqa: F401
    _WORKSPACE,
    SwarmError,
    _by_code,
    _counts,
    _handle_dir,
    _load_handle,
    _out_path,
    _paths,
    _resolve_any,
    _run,
    _save_handle,
    _short,
    _tool_env,
)
from swarm_support import (
    HERE as _HERE_ALIAS,
)
from swarm_support import (
    PACK as _PACK_ALIAS,
)
from swarm_test import (  # noqa: F401
    _SUMMARY,
    _pytest_summary,
    _resolve_artifacts_path,
    cmd_acceptance,
    cmd_gherkin_dry,
    cmd_gherkin_parse,
    cmd_pytest,
)
from swarm_uml import (  # noqa: F401
    _resolve_model,
    _uml_model_path,
    cmd_page,
    cmd_uml,
    cmd_uml_render,
    cmd_uml_scan,
    cmd_uml_sync,
)

# Backward-compat aliases expected by older callers/tests.
PACK = _PACK_ALIAS
HERE = _HERE_ALIAS

TOOLS = CORE_TOOLS + MODULES_TOOLS + QUALITY_TOOLS + TEST_TOOLS + UML_TOOLS + GATE_TOOLS
BY_NAME = {t["name"]: t for t in TOOLS}

COMMANDS = {
    "status": cmd_status,
    "doctor": cmd_doctor,
    "modules": cmd_modules,
    "interface": cmd_interface,
    "goal": cmd_goal,
    "envelope": cmd_envelope,
    "guide": cmd_guide,
    "check": cmd_check,
    "lint_record": cmd_lint_record,
    "decisions": cmd_decisions,
    "init_work": cmd_init_work,
    "clean": cmd_clean,
    "check_envelope": cmd_check_envelope,
    "vocab_rename": cmd_vocab_rename,
    "ruff": cmd_ruff,
    "dry": cmd_dry,
    "pytest": cmd_pytest,
    "crap": cmd_crap,
    "acceptance": cmd_acceptance,
    "gherkin_parse": cmd_gherkin_parse,
    "gherkin_dry": cmd_gherkin_dry,
    "uml_render": cmd_uml_render,
    "uml_sync": cmd_uml_sync,
    "uml_scan": cmd_uml_scan,
    "uml": cmd_uml,
    "page": cmd_page,
    "gate": cmd_gate,
    "ready": cmd_ready,
    "genRecord": cmd_gen_record,
    "genDoc": cmd_gen_doc,
    "report": cmd_report,
    "docs": cmd_docs,
    "help": cmd_help,
}


def _with_pack(result):
    """Stamp the result with the pack that answered.

    The same tool name exists in the project copy and in the clone. The path is
    the one field that tells the two apart.
    """
    if isinstance(result, dict):
        result.setdefault("pack", str(PACK))
    return result


def main(argv=None) -> int:
    argv = list(sys.argv if argv is None else argv)
    if len(argv) < 2:
        print(_help_text())
        return 0
    if argv[1] in ("-h", "--help"):
        print(_help_text(argv[2] if len(argv) > 2 else None))
        return 0
    if argv[1] == "help" and not (len(argv) > 2 and argv[2].lstrip().startswith("{")):
        print(_help_text(argv[2] if len(argv) > 2 else None))
        return 0
    if len(argv) > 2 and argv[2] in ("-h", "--help"):
        print(_help_text(argv[1]))
        return 0
    command = argv[1]
    raw = argv[2] if len(argv) > 2 else "{}"
    try:
        args = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError as error:
        print(json.dumps({"error": f"bad json args: {error}", "pack": str(PACK)}))
        return 0
    subsystem = args.get("subsystem")
    if subsystem:
        os.environ["SWARM_LANE"] = str(subsystem)
    handler = COMMANDS.get(command)
    if handler is None:
        result = {"error": f"unknown command: {command}", "known": sorted(COMMANDS)}
        print(json.dumps(_with_pack(result)))
        return 0
    try:
        result = handler(args)
    except Exception as error:  # noqa: BLE001  # one JSON error object, never a traceback
        result = {"error": f"{type(error).__name__}: {error}", "command": command}
        print(json.dumps(_with_pack(result)))
        return 0
    try:
        print(json.dumps(_with_pack(result), default=str))
    except BrokenPipeError:
        pass
    return 0


# Backward-compatible attribute propagation.
import types as _types

_SIBLING_MODULES = [
    sys.modules.get("swarm_support"),
    sys.modules.get("swarm_catalog_support"),
    sys.modules.get("swarm_core"),
    sys.modules.get("swarm_modules"),
    sys.modules.get("swarm_quality"),
    sys.modules.get("swarm_test"),
    sys.modules.get("swarm_uml"),
    sys.modules.get("swarm_gate"),
    sys.modules.get("swarm_help"),
]
_SIBLING_MODULES = [m for m in _SIBLING_MODULES if m is not None]


class _SwarmFacadeModule(_types.ModuleType):
    def __setattr__(self, name, value):
        super().__setattr__(name, value)
        for mod in _SIBLING_MODULES:
            if hasattr(mod, name):
                setattr(mod, name, value)


_facade = _SwarmFacadeModule(__name__)
_facade.__dict__.update(globals())
sys.modules[__name__] = _facade

if __name__ == "__main__":
    sys.exit(main())
