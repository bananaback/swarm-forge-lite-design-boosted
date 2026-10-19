"""Prompt and workflow conformance.

These tests pin the context-engineering invariants of the pack, so a later edit
cannot silently restore the defects a session audit found: oversized permission
blocks, a copied stop test, the stale cell-driver docs, and the unnamed work
directory. They also pin the one-division vocabulary: the scope is a subsystem,
the division is a module, and the seam is an interface.

They read the prompt files on purpose. The workflow is part of the product here;
these are the observable properties of it.
"""

from __future__ import annotations

from pathlib import Path

import questions

PACK = Path(__file__).resolve().parents[3]
AGENTS = PACK.parent / ".opencode" / "agents"
PROTOCOL = PACK / "protocol"
CONSTITUTION = PACK / "constitution" / "articles"
REFERENCE = PACK / "reference"
TEMPLATES = PACK / "design" / "templates"

WORKER_ROLES = (
    "interrogator",
    "specifier",
    "architect",
    "designer",
    "critic",
    "coder",
    "test-reviewer",
    "refactorer",
    "hotfixer",
)
DESIGN_ROLES = ("interrogator", "architect", "designer", "critic")

# Senses of "boundary" that are not the design-division sense.
BOUNDARY_VALUE_SENSE = (
    "boundary value",
    "boundary values",
    "exclusion boundary",
    "phase boundary",
    "a boundary",
    "real boundary",
)


def _agent(role: str) -> str:
    return (AGENTS / f"{role}.md").read_text(encoding="utf-8")


def _flat(text: str) -> str:
    """Collapse whitespace, so a phrase does not fail on a line wrap."""
    return " ".join(text.split())


def _permission_rules(text: str) -> list[str]:
    """The `- action:` rule lines inside the frontmatter permissions block."""
    lines = text.splitlines()
    start = next(i for i, line in enumerate(lines) if line.strip() == "permissions:")
    end = next(i for i in range(start + 1, len(lines)) if lines[i].strip() == "---")
    return [line for line in lines[start:end] if line.strip().startswith("- action:")]


def test_worker_permission_blocks_guard_git():
    """Each worker denies every git command, then allows the common read-only ones."""
    for role in WORKER_ROLES:
        text = _agent(role)
        rules = _permission_rules(text)
        assert 10 <= len(rules) <= 30, (
            f"{role}: unexpected permission block ({len(rules)} rules)"
        )
        body = text.split("permissions:", 1)[1]
        assert "resource: git *" in body and "effect: deny" in body, (
            f"{role}: no git deny"
        )
        for read in (
            "resource: git status *",
            "resource: git log *",
            "resource: git diff *",
            "resource: git show *",
        ):
            assert read in body, f"{role}: missing read allow {read}"


def test_no_git_wrapper_is_required():
    """The roles use plain git; there is no wrapper to learn."""
    for role in WORKER_ROLES:
        assert "gitro" not in _agent(role), f"{role}: still names a git wrapper"


def test_execution_rules_are_present():
    workflow = (CONSTITUTION / "workflow.md").read_text(encoding="utf-8")
    assert "## Execution" in workflow
    assert "Write the artifact as you go" in workflow
    assert "Run each command once" in workflow
    assert "Stop condition" in workflow


def test_gate_integrity_is_defined():
    communication = _flat(
        (CONSTITUTION / "communication.md").read_text(encoding="utf-8")
    )
    assert "Gate integrity" in communication
    assert "A new DECISION means `STATE: open`" in communication
    assert "Re-surface a decision" in communication


def test_settled_and_a_new_decision_never_coexist():
    design = _flat((PROTOCOL / "design-protocol.md").read_text(encoding="utf-8"))
    assert "A new DECISION makes `settled` illegal" in design


def test_dispatch_cites_paths_and_has_no_prompt_craft_commentary():
    dispatch = _flat((PROTOCOL / "dispatch.md").read_text(encoding="utf-8"))
    assert "Cite the Path" in dispatch
    assert "8 KB" not in dispatch
    assert "#CHANGE CLASS" in dispatch
    for banned in (
        "V4+ prompting guide",
        "where attention is exact",
        "Why content, not pointers",
        "it spends that slot",
    ):
        assert banned not in dispatch, f"dispatch still carries commentary: {banned!r}"


def test_stop_test_has_one_source_and_covers_every_role():
    quality = _flat((REFERENCE / "design-quality.md").read_text(encoding="utf-8"))
    assert "single source" in quality
    for role in WORKER_ROLES:
        assert role in questions.STOP_TESTS, f"no stop-test line for {role}"


def test_the_stale_cell_driver_documentation_is_gone():
    """The old cell driver drove one form cell at a time, and it is gone.

    The hand-maintained `index.md` is gone too: `swarm.guide` and
    `harness.py guide` list the forms, so a static copy only drifts.
    """
    assert not (TEMPLATES / "interrogator" / "index.md").exists()
    for path in sorted((TEMPLATES / "interrogator").glob("*.md")):
        text = path.read_text(encoding="utf-8").lower()
        for banned in (
            "questions interrogator --next",
            "harness.py answer",
            "one bounded cell at a time",
        ):
            assert banned not in text, (
                f"stale driver text remains in {path.name}: {banned!r}"
            )


def test_flat_init_writes_one_file_per_role(tmp_path):
    """A new subsystem gets one file per role, not a directory of forms."""
    for role, name in (
        ("interrogator", "requirements.md"),
        ("architect", "architecture.md"),
        ("critic", "review.md"),
    ):
        written = questions.emit_flat(role, tmp_path)
        assert [path.name for path in written] == [name]
    module = questions.emit_flat("designer", tmp_path, "engine")
    assert [path.name for path in module] == ["engine.md"]
    assert (tmp_path / "modules" / "engine.md").is_file()


def test_every_interrogator_section_is_checked_or_exempt():
    """A new section must be classified, so the rule never silently misses one."""
    import record

    forms = {section.file for section in questions.SPECS["interrogator"].sections}
    records = Path(record.__file__).resolve().parents[2] / "design" / "subsystems"
    in_use = {path.name for path in records.glob("*/01-interrogator/*.md")}
    classified = set(record.VOCABULARY_SECTIONS) | set(record.VOCABULARY_EXEMPT)
    missing = sorted((forms | in_use) - classified)
    assert not missing, f"unclassified sections: {missing}"


def test_decisions_tables_teach_the_option_separator():
    """Every flat template carries the DECISION table, so the parser never drifts."""
    for text in (
        questions.FLAT_MODULE,
        questions.FLAT_ARCHITECTURE,
        questions.FLAT_REVIEW,
    ):
        assert "| Dn | Question" in text


def test_flat_work_directories():
    """The record is flat: design roles work at the root, designers in modules/."""
    assert questions.work_dir_for("interrogator") == ""
    assert questions.work_dir_for("architect") == ""
    assert questions.work_dir_for("critic") == ""
    assert questions.work_dir_for("designer") == "modules"


def test_workflow_uses_one_term_per_concept():
    """One term for one concept. A synonym here confuses a role."""
    banned = ("slice", "checkpoint", "stop-test", "blueprint")
    for path in list(PROTOCOL.glob("*.md")) + list(AGENTS.glob("*.md")):
        # `12-stop-test.md` is a real generated file name, not the prose term.
        text = path.read_text(encoding="utf-8").lower().replace("12-stop-test.md", "")
        for word in banned:
            assert word not in text, f"{path.name} uses the synonym {word!r}"


def test_protocol_role_templates_are_unfilled_and_guarded():
    """A role answer template is a shared placeholder. No role may overwrite it."""
    roles = (
        "interrogator",
        "specifier",
        "architect",
        "designer",
        "critic",
        "coder",
        "test-reviewer",
        "refactorer",
        "hotfixer",
    )
    for role in roles:
        text = (PROTOCOL / f"{role}.md").read_text(encoding="utf-8")
        assert "Do not edit this file" in text, (
            f"{role}.md lost its shared-template guard"
        )
        if role == "hotfixer":
            first = next(
                (line for line in text.splitlines() if line.startswith("STATUS:")), ""
            )
        else:
            first = next(
                (line for line in text.splitlines() if line.startswith("SUBSYSTEM:")),
                "",
            )
        # A filled template carries a real value; a placeholder carries `<...>` or options.
        assert "<" in first or "|" in first, (
            f"{role}.md was overwritten with a real answer: {first!r}"
        )


def test_no_comment_and_no_docstring_are_taught():
    """The rule: write no comment and no docstring. Keep only a load-bearing line."""
    craft = (REFERENCE / "code-craft.md").read_text(encoding="utf-8")
    assert "## Comments" in craft
    assert "## Docstrings" in craft
    assert "Write no comment" in craft
    assert "Write no docstring" in craft
    assert "No design id in code" in craft
    for role in ("coder", "refactorer", "hotfixer"):
        assert "no comment and no docstring" in _agent(role).lower(), (
            f"{role} does not name the no-comment rule"
        )


def test_code_craft_is_taught_and_pointed_to():
    """The code craft is a reference, and every code-writing role points at it."""
    craft = (REFERENCE / "code-craft.md").read_text(encoding="utf-8")
    assert "Readability first" in craft
    assert "No one-liners" in craft
    assert "Do not show off" in craft
    assert "Earn its keep" in craft
    for role in ("coder", "refactorer", "hotfixer"):
        assert "code-craft.md" in _agent(role), (
            f"{role} does not point at code-craft.md"
        )


def test_scope_gate_and_economy_are_taught():
    """The scope gate and the earn-its-keep craft are present, in the pack and the roles."""
    craft = (REFERENCE / "design-craft-design.md").read_text(encoding="utf-8")
    assert "earn its keep" in craft
    assert "Never trade a guard" in craft
    assert "YAGNI" in craft
    quality = (REFERENCE / "design-quality.md").read_text(encoding="utf-8")
    assert "scope answer" in quality
    communication = (CONSTITUTION / "communication.md").read_text(encoding="utf-8")
    assert "scope gate" in communication
    procedure = (PROTOCOL / "design-procedure.md").read_text(encoding="utf-8")
    assert "Scope gate" in procedure
    for role in ("interrogator", "architect", "designer", "critic"):
        assert "scope" in _agent(role).lower(), f"{role} does not name the scope gate"


def test_file_length_convention_is_soft_and_code_only():
    """The length convention is taught, scoped to code files, and never a cap.

    The oracle is the constitution, which the pack ships. This test deliberately
    does not read PROJECT.md: that file is project-owned and never travels, so a
    pack test may not depend on its wording. The scan at the end only reports which
    band the code files fall in, so a long file stays visible without ever becoming
    a defect.
    """
    import json

    text = _flat((CONSTITUTION / "engineering.md").read_text(encoding="utf-8"))
    assert "soft length convention" in text, (
        "engineering.md does not teach the convention"
    )
    assert "never a cap" in text, (
        "engineering.md does not say the convention is not a cap"
    )
    assert "Docs, records and prompts are exempt" in text, (
        "engineering.md does not scope the convention to code files"
    )

    config = json.loads((PACK / "harness.json").read_text(encoding="utf-8"))
    roots = [PACK / entry["root"] for entry in config.get("persistent_tests", [])]
    bands = {"target <=100": 0, "normal <=250": 0, "longer, allowed": 0}
    longest = []
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*.py"):
            if any(
                part in (".hypothesis", "__pycache__", ".pytest_cache")
                for part in path.parts
            ):
                continue
            lines = len(path.read_text(encoding="utf-8", errors="replace").splitlines())
            if lines <= 100:
                bands["target <=100"] += 1
            elif lines <= 250:
                bands["normal <=250"] += 1
            else:
                bands["longer, allowed"] += 1
            longest.append((lines, str(path.relative_to(PACK.parent))))
    longest.sort(reverse=True)
    print(
        "code files by band: "
        + ", ".join(f"{name}={count}" for name, count in bands.items())
    )
    print(
        "longest (reported, never a defect): "
        + ", ".join(f"{path}:{lines}" for lines, path in longest[:5])
    )


def test_one_division_vocabulary():
    """The scope is a subsystem, the division is a module. No design-division
    `boundary` remains in the protocol or the role prompts."""
    for path in list(PROTOCOL.glob("*.md")) + list(AGENTS.glob("*.md")):
        text = _flat(path.read_text(encoding="utf-8")).lower()
        for allowed in BOUNDARY_VALUE_SENSE:
            text = text.replace(allowed, "")
        assert "boundar" not in text, (
            f"{path.name}: design vocabulary still says boundary"
        )
