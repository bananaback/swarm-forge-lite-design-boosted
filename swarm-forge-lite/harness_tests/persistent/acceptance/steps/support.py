"""Shared helpers for the harness acceptance step handlers.

Everything here drives the real tools in child processes. Temporary projects
live under pytest's ``tmp_path``; no handler imports a host project module or
touches the real project or ``.swarmforge``.
"""

import json
import os
import re
import shlex
import stat
import subprocess
import sys
from pathlib import Path

PACK_ROOT = Path(__file__).resolve().parents[4]
CRAP4PY = PACK_ROOT / "tools" / "refactorer" / "crap4py"
DRY4PY = PACK_ROOT / "tools" / "shared" / "dry4py"
RUFF4PY = PACK_ROOT / "tools" / "shared" / "ruff4py"
HARNESS = PACK_ROOT / "tools" / "shared" / "harness.py"

CLEARED_ENV = ("SWARM_CONFIG", "SWARM_PACK", "RUFF4PY_CONFIG")


def step(pattern: str, handler):
    """Bind a regex pattern to a handler that also receives the match."""

    def wrapped(world, params):
        match = re.compile(pattern).search(params["_step_text"])
        handler(world, params, match)

    return (pattern, wrapped)


def clean_env() -> dict:
    """The ambient environment with every harness override removed."""
    env = dict(os.environ)
    for key in CLEARED_ENV:
        env.pop(key, None)
    return env


def run_tool(tool, args, env: dict, cwd=None):
    """Run a tool entry point in a child process, capturing its output."""
    argv = [sys.executable, str(tool), *[str(arg) for arg in args]]
    return subprocess.run(argv, capture_output=True, text=True, env=env, cwd=cwd)


def write_text(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def write_executable(path: Path, text: str) -> Path:
    write_text(path, text)
    mode = path.stat().st_mode
    path.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return path


def write_config(project: Path, fields: dict) -> Path:
    """Write a harness.json under the project, resolving paths against it."""
    document = {"version": 1, **fields}
    return write_text(project / "harness.json", json.dumps(document, indent=2) + "\n")


def temp_project(world, name: str = "project") -> Path:
    """A fresh project directory under the scenario's pytest tmp_path."""
    counter = world.state.get("_project_count", 0)
    world.state["_project_count"] = counter + 1
    project = Path(world.tmp_path) / f"{name}-{counter}"
    project.mkdir(parents=True, exist_ok=True)
    return project


def python_command(script: Path) -> str:
    return f"{shlex.quote(sys.executable)} {shlex.quote(str(script))}"


FAKE_JSCPD = '''#!__PYTHON__
"""Recording stand-in for jscpd, driven by environment variables."""
import json
import os
import sys
from pathlib import Path


def main():
    record = os.environ.get("JSCPD_RECORD")
    if record:
        with open(record, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(sys.argv[1:]) + "\\n")
    stderr = os.environ.get("JSCPD_STDERR", "")
    if stderr:
        sys.stderr.write(stderr)
    if os.environ.get("JSCPD_WRITE_REPORT", "1") == "1":
        args = sys.argv[1:]
        output = None
        for index, token in enumerate(args):
            if token == "--output" and index + 1 < len(args):
                output = args[index + 1]
        target = Path(output)
        target.mkdir(parents=True, exist_ok=True)
        (target / "jscpd-report.json").write_text(
            os.environ.get("JSCPD_REPORT", '{"duplicates": []}'), encoding="utf-8"
        )
    sys.exit(int(os.environ.get("JSCPD_EXIT", "0")))


main()
'''

FAKE_RUFF = '''#!__PYTHON__
"""Recording stand-in for ruff, driven by environment variables."""
import json
import os
import sys

record = os.environ.get("RUFF_RECORD")
if record:
    with open(record, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(sys.argv[1:]) + "\\n")
sys.exit(int(os.environ.get("RUFF_EXIT", "0")))
'''


def install_fake_jscpd(bin_dir: Path) -> Path:
    return write_executable(
        bin_dir / "jscpd", FAKE_JSCPD.replace("__PYTHON__", sys.executable)
    )


def install_fake_ruff(bin_dir: Path) -> Path:
    return write_executable(
        bin_dir / "ruff", FAKE_RUFF.replace("__PYTHON__", sys.executable)
    )


def install_unrunnable_ruff(bin_dir: Path) -> Path:
    return write_executable(bin_dir / "ruff", "this is not an executable program\n")


def prepend_path(env: dict, directory: Path) -> dict:
    env["PATH"] = str(directory) + os.pathsep + env.get("PATH", "")
    return env


def recorded_invocations(record: Path) -> list:
    """Every argv list the recording fake wrote, oldest first."""
    if not record.exists():
        return []
    return [json.loads(line) for line in record.read_text().splitlines() if line]


def last_invocation(record: Path) -> list:
    invocations = recorded_invocations(record)
    assert invocations, f"the recording tool was never invoked ({record})"
    return invocations[-1]


def row_for(output: str, name: str) -> str:
    """The report row that mentions ``name``."""
    for line in output.splitlines():
        if name in line:
            return line
    raise AssertionError(f"no report row for {name!r} in:\n{output}")
