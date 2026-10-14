"""Tests for the new harness surfaces: envelope, decisions, check-envelope, guide.

These pin the context-engineering contracts of the tool: the paste-ready envelope
carries the ENV and the stop-test line; the decision ledger reads the gate from
one place; the budget lint fails an oversized dispatch.
"""

import json
from pathlib import Path

import harness
import pytest


def _cfg(tmp_path):
    config = tmp_path / "harness.json"
    config.write_text(
        json.dumps(
            {
                "workspace_root": ".",
                "state_root": "state",
                "artifacts_root": "artifacts",
                "hot_tests": "hot",
                "source_roots": ["src"],
            }
        )
    )
    return config


class FakePaths:
    def pack_root(self):
        return Path("/pack")

    def specs(self):
        class _Absent:
            def text(self):
                return "(none)"

        return _Absent()


def test_envelope_carries_the_stop_test_and_the_env(capsys):
    harness.cmd_envelope(
        harness.argparse.Namespace(role="architect", subsystem="t"), FakePaths()
    )
    out = capsys.readouterr().out
    assert "#ROLE" in out and "architect" in out
    assert (
        "#SUBSYSTEM" in out and "t" in out and "#WORK" in out and "02-architect/" in out
    )
    assert "#ENV" in out
    assert "#STOP TEST" in out
    assert "one secret per card" in out


def test_envelope_uses_the_numbered_work_directory(capsys):
    harness.cmd_envelope(
        harness.argparse.Namespace(
            role="designer", subsystem="t", module="engine-state"
        ),
        FakePaths(),
    )
    out = capsys.readouterr().out
    assert "design/subsystems/t/modules/engine-state/" in out


def test_check_envelope_passes_a_small_dispatch(tmp_path, capsys):
    path = tmp_path / "env.md"
    path.write_text("Implement: x\n#ENV\n- a\n#DONE\n1. ok\n")
    with pytest.raises(SystemExit) as exit_info:
        harness.main(["--config", str(_cfg(tmp_path)), "check-envelope", str(path)])
    assert exit_info.value.code == 0
    assert "pass" in capsys.readouterr().out


def test_check_envelope_has_no_size_limit(tmp_path, capsys):
    """A large envelope passes. A long paste with no cite is a hint, not a failure."""
    path = tmp_path / "env.md"
    path.write_text("Implement: x\n#ENV\n" + ("- " + "a" * 400 + "\n") * 200)
    with pytest.raises(SystemExit) as exit_info:
        harness.main(["--config", str(_cfg(tmp_path)), "check-envelope", str(path)])
    assert exit_info.value.code == 0
    out = capsys.readouterr().out
    assert "pass" in out and "no size limit" in out


def test_decisions_reads_the_gate_from_one_place(tmp_path, capsys):
    work = tmp_path / "w"
    work.mkdir()
    (work / "decisions.md").write_text(
        "| Dn | Rule | Question | Options | Operator answer |\n"
        "|----|------|----------|---------|-----------------|\n"
        "| D1 | CQS split | split observe? | a / b |  |\n"
        "| D2 | contradiction | keep the edge? | a / b | Keep the edges |\n",
        encoding="utf-8",
    )
    harness.main(
        ["--config", str(_cfg(tmp_path)), "decisions", "designer", "--work", str(work)]
    )
    out = capsys.readouterr().out
    assert "D1 [open]" in out
    assert "D2 [answered]" in out
    assert "decisions: 1 open" in out


def test_gen_record_writes_counts_from_the_model(tmp_path, monkeypatch):
    import swarm_json

    root = tmp_path / "design" / "subsystems" / "clip"
    root.mkdir(parents=True)
    (root / "model.json").write_text(
        json.dumps(
            {
                "packages": [
                    {
                        "classes": [
                            {
                                "ops": [
                                    {"annotations": {"cqs": "command"}},
                                    {"annotations": {"cqs": "query"}},
                                ]
                            },
                            {"ops": []},
                        ]
                    }
                ],
                "edges": [{}, {}, {}],
                "levels": [["a"], ["b"]],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(swarm_json, "PACK", tmp_path)
    result = swarm_json.cmd_gen_record({"subsystem": "clip"})
    assert result["classes"] == 2
    assert result["ops"] == 2
    assert result["commands"] == 1
    assert result["queries"] == 1
    assert result["edges"] == 3
    text = (root / "COUNTS.md").read_text(encoding="utf-8")
    assert "| ops | 2 |" in text and "Do not hand-edit" in text
    contracts = (root / "CONTRACTS.md").read_text(encoding="utf-8")
    assert "| method | CQS |" in contracts and "Do not hand-edit" in contracts


def test_gen_record_projects_the_union_skeleton_from_the_modules(tmp_path, monkeypatch):
    import swarm_json

    root = tmp_path / "design" / "subsystems" / "clip"
    for module in ("alpha", "beta"):
        (root / "modules" / module).mkdir(parents=True)
    (root / "04-critic").mkdir(parents=True)
    (root / "model.json").write_text(
        json.dumps({"packages": [], "edges": [], "levels": []}), encoding="utf-8"
    )
    (root / "modules" / "alpha" / "SKELETON.md").write_text(
        "# SKELETON — clip · alpha\n\ncontract A\n", encoding="utf-8"
    )
    (root / "modules" / "beta" / "SKELETON.md").write_text(
        "# SKELETON — clip · beta\n\ncontract B\n", encoding="utf-8"
    )
    (root / "04-critic" / "3-skeleton.md").write_text(
        "## 3. SKELETON\n\nthe brief\n", encoding="utf-8"
    )
    monkeypatch.setattr(swarm_json, "PACK", tmp_path)

    result = swarm_json.cmd_gen_record({"subsystem": "clip"})
    assert result["skeleton"].endswith("SKELETON.md")
    text = (root / "SKELETON.md").read_text(encoding="utf-8")
    assert "GENERATED by swarm.genRecord" in text
    assert "## MODULE — alpha" in text and "contract A" in text
    assert "## MODULE — beta" in text and "contract B" in text
    assert "the brief" in text


def test_gen_record_leaves_the_union_alone_without_modules(tmp_path, monkeypatch):
    import swarm_json

    root = tmp_path / "design" / "subsystems" / "clip"
    root.mkdir(parents=True)
    (root / "model.json").write_text(
        json.dumps({"packages": [], "edges": [], "levels": []}), encoding="utf-8"
    )
    monkeypatch.setattr(swarm_json, "PACK", tmp_path)

    result = swarm_json.cmd_gen_record({"subsystem": "clip"})
    assert result["skeleton"] is None
    assert not (root / "SKELETON.md").exists()


def test_gen_record_never_overwrites_a_hand_written_union(tmp_path, monkeypatch):
    """The union carries the critic's cross-module prose. A projection must not erase it."""
    import swarm_json

    root = tmp_path / "design" / "subsystems" / "clip"
    (root / "modules" / "alpha").mkdir(parents=True)
    (root / "model.json").write_text(
        json.dumps({"packages": [], "edges": [], "levels": []}), encoding="utf-8"
    )
    (root / "modules" / "alpha" / "SKELETON.md").write_text(
        "# alpha\n", encoding="utf-8"
    )
    hand = "# SKELETON — clip\n\nThe critic's cross-module synthesis.\n"
    (root / "SKELETON.md").write_text(hand, encoding="utf-8")
    monkeypatch.setattr(swarm_json, "PACK", tmp_path)

    result = swarm_json.cmd_gen_record({"subsystem": "clip"})
    assert (root / "SKELETON.md").read_text(encoding="utf-8") == hand
    assert "left it alone" in result["note"]


def test_check_envelope_hints_at_a_paste_without_a_cite():
    import swarm_json

    result = swarm_json.cmd_check_envelope({"text": "#SCOPE\n" + ("x" * 400)})
    assert result["pass"] is True
    assert result["has_cite"] is False
    assert result["hint"] == "cite the path, do not paste"
    cited = swarm_json.cmd_check_envelope(
        {"text": "#SCOPE\nsee protocol/dispatch.md:62\n" + ("x" * 400)}
    )
    assert cited["has_cite"] is True and cited["hint"] is None


def test_guide_lists_a_design_role_form_and_stop_test(capsys):
    harness.cmd_guide(
        harness.argparse.Namespace(role="critic", subsystem="t"), FakePaths()
    )
    out = capsys.readouterr().out
    assert "HOW YOU WORK" in out
    assert "init-work critic" in out
    assert "STOP TEST (pass line)" in out


def test_form_serves_a_template_role_and_the_interrogator(monkeypatch, tmp_path):
    """`swarm.form` must work for every role that names it, not only the interrogator."""
    import swarm_json

    templates = tmp_path / "design" / "templates" / "architect"
    templates.mkdir(parents=True)
    (templates / "3-structure.md").write_text("## 3. STRUCTURE\n", encoding="utf-8")
    (templates / "index.md").write_text("map\n", encoding="utf-8")
    monkeypatch.setattr(swarm_json, "PACK", tmp_path)

    out = swarm_json.cmd_form({"role": "architect", "file": "3-structure.md"})
    assert out["file"] == "3-structure.md"
    assert out["text"].startswith("## 3. STRUCTURE")

    with pytest.raises(swarm_json.SwarmError) as err:
        swarm_json.cmd_form({"role": "architect", "file": "nope.md"})
    assert "3-structure.md" in str(err.value)

    items = swarm_json.cmd_form({"role": "interrogator", "file": "8-constraints.md"})
    assert items["title"].startswith("8. CONSTRAINTS")
    assert items["items"]


class _Paths:
    def __init__(self, artifacts):
        self._a = artifacts

    def artifacts_root(self):
        return self._a


def test_gherkin_dry_resolves_the_path_that_gherkin_parse_returns(
    tmp_path, monkeypatch
):
    """The two gherkin tools must chain: parse returns a workspace path, dry takes it."""
    import swarm_json

    ws = tmp_path
    artifacts = ws / "dump" / "clip"
    artifacts.mkdir(parents=True)
    ir = artifacts / "clip.json"
    ir.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(swarm_json, "_WORKSPACE", ws)

    paths = _Paths(artifacts)
    # the bare name, the artifacts-relative path, the workspace path, and the absolute path
    for raw in ("clip.json", "dump/clip/clip.json", str(ir)):
        assert swarm_json._resolve_artifacts_path(raw, paths) == ir
    assert swarm_json._resolve_artifacts_path("missing.json", paths) is None


def test_envelope_and_guide_agree_on_which_roles_have_a_work_directory():
    """One rule for the envelope and the guide: a role without a record dir gets ARTIFACTS."""
    import swarm_json

    def has_work(role):
        return (
            "WORK"
            in swarm_json.cmd_envelope({"role": role, "subsystem": "clip"})["fields"]
        )

    for role in ("interrogator", "architect", "critic"):
        assert has_work(role), role
    for role in ("test-reviewer", "refactorer", "hotfixer"):
        assert not has_work(role), role
    # the two note dirs the layout defines
    for role in ("specifier", "coder"):
        assert has_work(role), role


def test_a_missing_record_and_a_missing_subsystem_raise_a_clean_error():
    """An unknown subsystem must not report a passed lint, and a bare call must not crash."""
    import swarm_json

    with pytest.raises(swarm_json.SwarmError) as missing:
        swarm_json.cmd_lint_record({"subsystem": "definitely-not-a-subsystem"})
    assert "no such record" in str(missing.value)

    with pytest.raises(swarm_json.SwarmError) as bare:
        swarm_json.cmd_decisions({"role": "architect"})
    assert "pass subsystem or work" in str(bare.value)


def test_uml_scan_writes_under_the_artifacts_root(monkeypatch, tmp_path):
    """The scanned root is the SOURCE tree. A generated model must never land in it."""
    import swarm_json

    captured = {}

    def fake_run(argv, **kwargs):
        captured["argv"] = list(argv)
        return 0, "", ""

    monkeypatch.setattr(swarm_json, "_run", fake_run)
    monkeypatch.setattr(swarm_json, "_paths", lambda: _Paths(tmp_path / "dump"))
    monkeypatch.setattr(
        swarm_json, "_resolve_any", lambda raw, paths=None: tmp_path / "src"
    )

    swarm_json.cmd_uml_scan({"root": "src"})
    argv = captured["argv"]
    out = argv[argv.index("--out") + 1]
    assert out.startswith(str(tmp_path / "dump"))
    assert not out.startswith(str(tmp_path / "src"))
