"""Rule 27 — every command documents itself and `--help` exits 0.

These tests are the floor of the suite: no project is selected, no project tree
is read, and no network is used. They still need a parseable config, because
`paths.py` loads it at import time — a defect recorded in the plan for Phase 1,
where a missing config must produce "run tools/install.py", not a traceback.
"""

from __future__ import annotations

from pathlib import Path

import pytest

PACK = Path(__file__).resolve().parents[2]

COMMANDS = [
    ("tools/design/arch.py", ("--help",)),
    ("tools/design/arch.py", ("classes", "--help")),
    ("tools/design/arch.py", ("runtime", "--help")),
    ("tools/design/arch.py", ("docs", "--help")),
    ("tools/design/arch.py", ("render", "--help")),
    ("tools/umlview", ("--help",)),
]


@pytest.mark.parametrize(("tool", "args"), COMMANDS)
def test_help_exits_zero(run_tool, tool, args):
    result = run_tool(tool, *args)

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip(), f"{tool} {args} printed no help"


@pytest.mark.parametrize(
    ("module", "tools_path"),
    [("dryer", "shared"), ("crapper", "refactorer")],
)
def test_analyzer_help_exits_zero(run_tool, module, tools_path):
    result = run_tool(
        "-m",
        module,
        "--help",
        env={"PYTHONPATH": str(PACK / "tools" / tools_path)},
    )

    assert result.returncode == 0, result.stderr
    assert "Usage" in result.stdout, f"{module} printed no usage"


def test_unknown_subcommand_is_a_user_error(run_tool):
    result = run_tool("tools/design/arch.py", "nonsense")

    assert result.returncode == 2
    assert "invalid choice" in result.stderr
