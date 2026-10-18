"""The workflow invariants that a fresh agent depends on.

Every test here protects a way the chain can silently break for an agent that has
no warm context: a tool that no prompt names, a prompt that names a tool that no
longer exists, a generated file that lands in a source tree, or two tools that
disagree about the same path.

Each test states the behavior, not the wording.
"""

import json
import re
from pathlib import Path

import pytest
import swarm_json
import swarm_support

PACK = Path(__file__).resolve().parents[3]
AGENTS = PACK.parent / ".opencode" / "agents"
PLUGIN = PACK.parent / ".opencode" / "plugins" / "swarm-tools" / "index.ts"

# The role ids of the pipeline, plus the two role groups the catalog may use.
ROLES = {
    "orchestrator",
    "specifier",
    "interrogator",
    "architect",
    "designer",
    "critic",
    "coder",
    "test-reviewer",
    "refactorer",
    "hotfixer",
}
GROUPS = {"all": ROLES, "design team": {"architect", "designer", "critic"}}


def catalog():
    return {t["name"]: t for t in swarm_json.TOOLS}


def prompt_tools():
    return {
        f.stem: set(re.findall(r"swarm\.([A-Za-z]+)\(", f.read_text(encoding="utf-8")))
        for f in AGENTS.glob("*.md")
    }


def declared(roles: str) -> set:
    out = set()
    for part in (p.strip() for p in roles.split(",")):
        if part:
            out |= GROUPS.get(part, {part})
    return out


def backend_name(tool: str) -> str:
    """The dispatch key of a tool. The catalog is camelCase; the backend is snake_case."""
    snake = re.sub(r"(?<!^)(?=[A-Z])", "_", tool).lower()
    return snake if snake in swarm_json.COMMANDS else tool


def test_every_catalogued_tool_is_reachable_by_the_backend():
    """A catalogued tool that the backend cannot dispatch is a dead end for an agent."""
    for name in catalog():
        assert backend_name(name) in swarm_json.COMMANDS, name
        assert swarm_json.cmd_help({"tool": name})["name"] == name, name


def test_every_tool_carries_what_an_agent_needs_to_use_it():
    """Summary, example, a note, the roles, and a named return shape."""
    for name, tool in catalog().items():
        assert tool["summary"].strip(), f"{name}: no summary"
        assert tool["example"].strip(), f"{name}: no example"
        assert tool["notes"].strip(), f"{name}: no note on when to use it"
        assert tool["roles"].strip(), f"{name}: no roles"
        assert tool["returns"].strip(), f"{name}: no return shape"


def test_every_declared_role_is_a_real_role():
    """A typo in a role name sends an agent looking for a role that does not exist."""
    for name, tool in catalog().items():
        for role in declared(tool["roles"]):
            assert role in ROLES, f"{name}: unknown role {role!r}"


def test_every_prompt_names_only_tools_that_exist():
    """A prompt that names a removed tool makes the agent call nothing and stall."""
    known = catalog()
    for role, named in prompt_tools().items():
        unknown = sorted(named - known.keys())
        assert not unknown, f"{role}: names {unknown}"


def test_the_prompts_and_the_catalog_agree_on_who_owns_each_tool():
    """One owner list. A prompt and the catalog that disagree lose an agent turns."""
    named = prompt_tools()
    for name, tool in catalog().items():
        users = {role for role, tools in named.items() if name in tools}
        assert users <= declared(tool["roles"]), (
            f"{name}: prompts say {sorted(users)}, "
            f"catalog omits {sorted(users - declared(tool['roles']))}"
        )


def test_every_tool_the_plugin_registers_is_catalogued_and_the_reverse():
    """An agent reaches a tool only through the plugin, so the two lists must match."""
    text = PLUGIN.read_text(encoding="utf-8")
    registered = set(re.findall(r"\badd\(\s*\n\s*\"([A-Za-z]+)\"", text))
    assert registered == set(catalog())


def test_the_doctor_checks_the_agent_model_plan(monkeypatch, tmp_path):
    """A declared model variant must exist; an external provider is reported, not failed."""
    import swarm_gate

    workspace = tmp_path / "work"
    pack = workspace / "swarm-forge-lite"
    agents = workspace / ".opencode" / "agents"
    pack.mkdir(parents=True)
    agents.mkdir(parents=True)
    (agents / "probe.md").write_text("---\nmodel: p/m#high\n---\n", encoding="utf-8")
    (workspace / "opencode.json").write_text(
        json.dumps(
            {
                "model": "p/m#high",
                "providers": {"p": {"models": {"m": {"variants": [{"id": "high"}]}}}},
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(swarm_gate, "PACK", pack)
    checks = swarm_gate._model_checks()
    assert checks[0]["ok"] is True
    assert "1 agents" in checks[0]["detail"]

    (agents / "probe.md").write_text("---\nmodel: p/m#low\n---\n", encoding="utf-8")
    assert swarm_gate._model_checks()[0]["ok"] is False


def test_the_board_and_todo_are_wired_into_the_orchestrator():
    """A template no prompt reads is paperwork; a rule no file backs is a guess."""
    templates = PACK / "design" / "templates"
    board = (templates / "TASK_BOARD.md").read_text(encoding="utf-8")
    todo = (templates / "TODO.md").read_text(encoding="utf-8")
    assert "| Session | Subsystem | Doing |" in board
    assert "Stale" not in board and "Touched" not in board
    assert "| Id | Goal | Subsystem | Ready |" in todo
    orchestrator = (AGENTS / "orchestrator.md").read_text(encoding="utf-8")
    assert "#OTHER SESSIONS" in orchestrator
    assert "design/TASK_BOARD.md" in orchestrator
    assert "pick the todo goal" in orchestrator


def test_the_plugin_readme_tool_table_is_generated_from_the_catalog():
    """The README table must be the catalog's own table, not a hand copy."""
    from swarm_help import tool_table

    readme = PLUGIN.parent / "README.md"
    assert tool_table() in readme.read_text(encoding="utf-8")


def test_a_bare_output_name_goes_to_the_artifacts_root(monkeypatch, tmp_path):
    """A generated model must never land at the workspace root or in a source tree."""
    artifacts = tmp_path / "dump"
    artifacts.mkdir()
    monkeypatch.setattr(swarm_support, "_WORKSPACE", tmp_path)
    monkeypatch.setattr(swarm_json, "_paths", lambda: _Paths(artifacts))

    out = swarm_json._out_path("scan.json")
    assert out.parent == artifacts


def test_an_explicit_record_path_is_left_where_the_caller_means(monkeypatch, tmp_path):
    """A caller that names a record file keeps it, so the model tools stay idempotent."""
    artifacts = tmp_path / "dump"
    artifacts.mkdir()
    record = tmp_path / "design" / "subsystems" / "clip"
    record.mkdir(parents=True)
    monkeypatch.setattr(swarm_support, "_WORKSPACE", tmp_path)
    monkeypatch.setattr(swarm_json, "_paths", lambda: _Paths(artifacts))

    out = swarm_json._out_path("design/subsystems/clip/model.html")
    assert out == record / "model.html"


def test_the_envelope_and_the_guide_name_the_same_paths_for_every_role():
    """The two tools that hand a role its paths must never disagree."""
    for role in sorted(ROLES):
        envelope = swarm_json.cmd_envelope({"role": role, "subsystem": "clip"})[
            "fields"
        ]
        guide = swarm_json.cmd_guide({"role": role, "subsystem": "clip"})
        assert ("WORK" in envelope) == ("work" in guide), role
        assert ("ARTIFACTS" in envelope) == ("artifacts" in guide), role


def test_every_pipeline_role_has_a_stop_test():
    """`swarm.ready` and the envelope both carry it, so a gap breaks the gate."""
    for role in sorted(ROLES - {"orchestrator"}):
        assert swarm_json.questions.STOP_TESTS.get(role), role


def test_every_role_envelope_carries_its_stop_test():
    """A dispatch without the pass clauses sends the role back to the protocol."""
    for role in sorted(ROLES - {"orchestrator"}):
        envelope = swarm_json.cmd_envelope({"role": role, "subsystem": "clip"})
        assert (envelope.get("stop_test") or "").strip(), role
        assert "#STOP TEST" in envelope["text"], role


def test_every_finding_the_linter_raises_carries_a_fix(tmp_path):
    """An agent that gets a finding must be able to look up its one-line fix."""
    import record

    path = tmp_path / "7-requirements.md"
    path.write_text(
        "# REQUIREMENTS\n\n"
        "| Rn | EARS | Statement | Scale | Meter | Target | Verification | Refines |\n"
        "|---|---|---|---|---|---|---|---|\n"
        "| R1 | Ubiquitous | The ClipRecorder shall write the file. | a | b | c | test | G9.9 |\n"
        "| R1 | Ubiquitous | a second row under the same number | a | b | c | test | G1 |\n",
        encoding="utf-8",
    )
    report = record.lint_documents({"7-requirements.md": record.Document.read(path)})
    codes = {f.code for f in report.findings}
    assert codes, "the crafted document must raise at least one finding"
    for code in codes:
        assert record.HINTS.get(code), code
    assert all("\n" not in record.HINTS[c] for c in codes)


def test_a_malformed_decision_row_is_surfaced_not_dropped(tmp_path):
    """A row with a shifted column would misread the answer, so report it, do not skip."""
    import harness

    work = tmp_path / "04-critic"
    work.mkdir()
    (work / "decisions.md").write_text(
        "| Dn | Rule | Question | Options | Answer |\n"
        "|---|---|---|---|---|\n"
        "| D1 | a rule | a question | (a) / (b) | (a) | a stray cell |\n",
        encoding="utf-8",
    )
    rows, _open_count, found = harness.read_decision_rows(work)
    assert found
    assert [r["status"] for r in rows] == ["malformed"]


def test_every_role_prompt_resolves_the_roots_with_its_own_lane():
    """A bare `status()` returns un-scoped roots, so the role loses its lane."""
    for f in AGENTS.glob("*.md"):
        text = f.read_text(encoding="utf-8")
        assert "swarm.status(" in text, f"{f.stem} never resolves the roots"
        assert "swarm.status()" not in text, (
            f"{f.stem} resolves the roots without its lane"
        )


def test_every_tool_a_role_uses_in_a_step_is_listed_in_its_tools():
    """A fresh agent reads `<tools>` to learn what it has. A step that uses an
    unlisted tool leaves the agent to infer it, or to stall."""
    for f in AGENTS.glob("*.md"):
        text = f.read_text(encoding="utf-8")
        block = re.search(r"<tools>(.*?)</tools>", text, re.DOTALL)
        if not block:
            continue
        listed = set(re.findall(r"swarm\.([A-Za-z]+)\(", block.group(1)))
        used = set(re.findall(r"swarm\.([A-Za-z]+)\(", text[block.end() :]))
        assert not (used - listed), (
            f"{f.stem}: uses {sorted(used - listed)} but does not list them"
        )


def test_the_tool_environment_scopes_every_disposable_root_to_the_lane(
    tmp_path, monkeypatch
):
    """A tool run must give the same scoped environment as the lane wrapper."""
    artifacts = tmp_path / "dump"
    artifacts.mkdir()
    monkeypatch.setattr(swarm_json, "_paths", lambda: _Paths(artifacts))

    env = swarm_json._tool_env(swarm_json._paths())
    for key in (
        "SWARM_TEST_DATA",
        "PYTHONPYCACHEPREFIX",
        "TMPDIR",
        "HYPOTHESIS_STORAGE_DIRECTORY",
    ):
        assert key in env, key
        assert env[key].startswith(str(artifacts)), key


def test_the_pytest_summary_reads_the_counts_and_the_failing_tests():
    """A role reports its VERIFY from this. A missed failure hides a red tree."""
    log = (
        "..F\n"
        "FAILED tests/unit/test_a.py::test_x - AssertionError: nope\n"
        "ERROR tests/unit/test_b.py::test_y\n"
        "=== 5 passed, 1 failed, 2 errors in 1.2s ===\n"
    )
    summary = swarm_json._pytest_summary(log)
    assert summary["tallies"] == {"passed": 5, "failed": 1, "errors": 2}
    assert [f["test"] for f in summary["failures"]] == [
        "tests/unit/test_a.py::test_x",
        "tests/unit/test_b.py::test_y",
    ]
    assert "nope" in summary["failures"][0]["reason"]


def test_ready_passes_only_when_every_part_passes(monkeypatch):
    """The record gate is an AND. One red part or one open decision must fail it."""
    monkeypatch.setattr(
        swarm_json,
        "cmd_check",
        lambda a: {
            "passed": True,
            "errors": 0,
            "warnings": 0,
            "byCode": {},
            "ok": True,
        },
    )
    monkeypatch.setattr(
        swarm_json,
        "cmd_lint_record",
        lambda a: {"passed": True, "errors": 0, "ok": True},
    )
    monkeypatch.setattr(swarm_json, "cmd_decisions", lambda a: {"open": 0, "ok": True})
    assert swarm_json.cmd_ready({"role": "critic", "subsystem": "x"})["pass"] is True

    monkeypatch.setattr(swarm_json, "cmd_decisions", lambda a: {"open": 1, "ok": False})
    assert swarm_json.cmd_ready({"role": "critic", "subsystem": "x"})["pass"] is False

    monkeypatch.setattr(swarm_json, "cmd_decisions", lambda a: {"open": 0, "ok": True})
    monkeypatch.setattr(
        swarm_json,
        "cmd_check",
        lambda a: {
            "passed": False,
            "errors": 1,
            "warnings": 0,
            "byCode": {"x": 1},
            "ok": False,
        },
    )
    assert swarm_json.cmd_ready({"role": "critic", "subsystem": "x"})["pass"] is False


def test_a_record_command_without_a_subsystem_or_work_raises_cleanly():
    """A missing selector must be a SwarmError, never a TypeError on a None path."""
    for command in (swarm_json.cmd_check, swarm_json.cmd_decisions):
        with pytest.raises(swarm_json.SwarmError, match="subsystem or work"):
            command({"role": "architect"})


def test_ready_uses_each_commands_ok_verdict(monkeypatch):
    """A command that says ok:false fails the gate even when its counts look clean."""
    monkeypatch.setattr(
        swarm_json, "cmd_check", lambda a: {"passed": True, "errors": 0, "ok": False}
    )
    monkeypatch.setattr(
        swarm_json,
        "cmd_lint_record",
        lambda a: {"passed": True, "errors": 0, "ok": True},
    )
    monkeypatch.setattr(swarm_json, "cmd_decisions", lambda a: {"open": 0, "ok": True})
    assert swarm_json.cmd_ready({"role": "critic", "subsystem": "x"})["pass"] is False


def test_gate_passes_only_when_every_check_is_clean(monkeypatch):
    """The terminal gate is an AND. One finding must fail it."""
    monkeypatch.setattr(swarm_json, "cmd_dry", lambda a: {"total": 0, "ok": True})
    monkeypatch.setattr(
        swarm_json, "cmd_ruff", lambda a: {"total": 0, "byCode": {}, "ok": True}
    )
    checks = {"subsystem": "x", "checks": ["dry", "ruff"]}
    assert swarm_json.cmd_gate(checks)["pass"] is True

    monkeypatch.setattr(swarm_json, "cmd_dry", lambda a: {"total": 3, "ok": False})
    assert swarm_json.cmd_gate(checks)["pass"] is False


def test_a_saved_handle_pages_its_rows(tmp_path, monkeypatch):
    """`view:'all'` gives a handle and `page` walks it, so a large list stays readable."""
    artifacts = tmp_path / "dump"
    artifacts.mkdir()
    monkeypatch.setattr(swarm_json, "_paths", lambda: _Paths(artifacts))
    rows = [{"n": i} for i in range(7)]

    handle = swarm_json._save_handle(rows, swarm_json._paths(), "probe")
    page = swarm_json.cmd_page({"handle": handle, "offset": 0, "limit": 3})
    assert page["total"] == 7
    assert page["returned"] == 3
    assert page["next"] == 3
    last = swarm_json.cmd_page({"handle": handle, "offset": 6, "limit": 3})
    assert last["returned"] == 1
    assert last["next"] is None

    try:
        swarm_json.cmd_page({"handle": "no-such-handle"})
    except swarm_json.SwarmError as err:
        assert "no such handle" in str(err)
    else:
        raise AssertionError("an unknown handle must raise")


def test_every_cli_result_carries_the_pack_that_answered(capsys):
    """Two packs hold the same tool names, so every result names the one that ran.

    The project copy and the clone both resolve `swarm-forge-lite`. An agent that
    reads the wrong pair has no other evidence to correct itself, and the error
    path is the one a lost agent sees first.
    """
    assert swarm_json.main(["docs", "{}"]) == 0
    assert json.loads(capsys.readouterr().out)["pack"] == str(PACK)

    assert swarm_json.main(["not-a-command", "{}"]) == 0
    failure = json.loads(capsys.readouterr().out)
    assert failure["pack"] == str(PACK)
    assert "error" in failure


class _Paths:
    def __init__(self, artifacts):
        self._artifacts = artifacts

    def artifacts_root(self):
        return self._artifacts

    def persistent_roots(self):
        return []

    def source_roots(self):
        return []
