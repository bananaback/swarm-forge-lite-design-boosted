"""Unit tests for the record linter (tools/shared/record.py)."""

from pathlib import Path

import record


def _write(directory: Path, name: str, text: str) -> Path:
    path = directory / name
    path.write_text(text, encoding="utf-8")
    return path


REQUIREMENTS_OK = """# REQUIREMENTS

| Rn | EARS | Statement | Scale | Meter | Target | Verification | Refines |
|---|---|---|---|---|---|---|---|
| R1 | Ubiquitous | The engine shall name its outcome YES or NO. | words | read it | 2 words | inspection | G1.1 |

## Acceptance Criteria

| ACn | Rn | Check |
|---|---|---|
| AC1 | R1 | 2 words, 0 others |
"""

GOAL_OK = """# GOAL

| Node | Type | Statement | Refines | Disposition |
|---|---|---|---|---|
| G1 | G | the top goal | - | top |
| G1.1 | R | the leaf | G1 | leaf -> R1 |

| Anti-goal | Against goal | We would have failed if |
|---|---|---|
| A1 | G1 | the outcome is named by a third word |
"""

TRACE_OK = """# TRACEABILITY

| Rn | Goal | Cn | Xn | ACn | Scenario | Contract | Test |
|---|---|---|---|---|---|---|---|
| R1 | G1.1 | - | - | AC1 | - | - | test_vocabulary |
"""


def test_clean_record_passes(tmp_path):
    _write(tmp_path, "7-requirements.md", REQUIREMENTS_OK)
    _write(tmp_path, "goal.md", GOAL_OK)
    _write(tmp_path, "11-traceability.md", TRACE_OK)
    report = record.lint_task(tmp_path)
    assert report.errors == []
    assert report.passed()


def test_adjacent_tables_are_parsed_separately():
    text = (
        "| Node | Refines |\n|---|---|\n| G1 | - |\n"
        "| Anti-goal | Against goal | We would have failed if |\n|---|---|---|\n"
        "| A1 | G1 | x |\n"
    )
    doc = record.Document(
        Path("x.md"),
        text,
        tuple(text.splitlines()),
        tuple(record.parse_tables(Path("x.md"), text)),
    )
    assert len(doc.tables) == 2
    assert doc.tables[0].header == ("Node", "Refines")
    assert doc.tables[1].header[0] == "Anti-goal"


def test_ears_count_must_be_exactly_one(tmp_path):
    _write(
        tmp_path,
        "7-requirements.md",
        """# R
| Rn | EARS | Statement | Scale | Meter | Target | Verification |
|---|---|---|---|---|---|---|
| R1 | Ubiquitous, When x | s | s | m | 1 | test |
""",
    )
    report = record.lint_task(tmp_path)
    assert any(f.code == "ears-count" for f in report.errors)


def test_verification_must_be_exactly_one(tmp_path):
    _write(
        tmp_path,
        "7-requirements.md",
        """# R
| Rn | EARS | Statement | Scale | Meter | Target | Verification |
|---|---|---|---|---|---|---|
| R1 | Ubiquitous | s | s | m | 1 | test, inspection |
""",
    )
    report = record.lint_task(tmp_path)
    assert any(f.code == "verification-count" for f in report.errors)


def test_fit_criterion_fields_are_required(tmp_path):
    _write(
        tmp_path,
        "7-requirements.md",
        """# R
| Rn | EARS | Statement | Scale | Meter | Target | Verification |
|---|---|---|---|---|---|---|
| R1 | Ubiquitous | s | s | m |  | test |
""",
    )
    report = record.lint_task(tmp_path)
    assert any(f.code == "fit-missing" for f in report.errors)


def test_requirement_without_acceptance_criterion(tmp_path):
    _write(
        tmp_path,
        "7-requirements.md",
        """# R
| Rn | EARS | Statement | Scale | Meter | Target | Verification |
|---|---|---|---|---|---|---|
| R1 | Ubiquitous | s | s | m | 1 | test |
""",
    )
    report = record.lint_task(tmp_path)
    assert any(f.code == "rn-no-acn" for f in report.errors)


def test_machine_noun_is_a_warning(tmp_path):
    _write(
        tmp_path,
        "7-requirements.md",
        """# R
| Rn | EARS | Statement | Scale | Meter | Target | Verification |
|---|---|---|---|---|---|---|
| R1 | Ubiquitous | the FooBar calls `engine.py` | s | m | 1 | test |

| ACn | Rn | Check |
|---|---|---|
| AC1 | R1 | ok |
""",
    )
    report = record.lint_task(tmp_path)
    assert any(f.code == "machine-noun" for f in report.warnings)
    assert not any(f.code == "machine-noun" for f in report.errors)


def test_machine_noun_is_flagged_outside_the_requirement_statement(tmp_path):
    """A leak in a constraint row is a defect, not only one in a statement."""
    _write(
        tmp_path,
        "8-constraints.md",
        """# CONSTRAINTS

| Cn | Sentence | Classification |
|---|---|---|
| C1 | The kept state shall live in `KeptState`. | Fixed |
""",
    )
    report = record.lint_task(tmp_path)
    assert any(f.code == "machine-noun" and f.line == 5 for f in report.warnings)


def test_machine_noun_is_flagged_in_the_spec_document(tmp_path):
    """The spec document is read with the record, so a leak in it is a defect."""
    record_dir = tmp_path / "subsystems" / "alpha"
    record_dir.mkdir(parents=True)
    specs = tmp_path / "specs"
    specs.mkdir()
    _write(specs, "04-alpha.md", "- R1 — the recorder reads `app/pipeline/sink.py`.\n")
    _write(record_dir, "0-frame.md", "# FRAME\n")
    report = record.lint_task(record_dir, specs)
    assert any(f.code == "machine-noun" for f in report.warnings)


def test_the_design_record_may_name_a_class(tmp_path):
    """The design record names classes on purpose. It is not a business document."""
    _write(
        tmp_path,
        "2-crc-cards.md",
        """# CRC

| Card | Responsibility |
|---|---|
| `KeptState` | Hold the switch latch. |
""",
    )
    report = record.lint_task(tmp_path)
    assert not any(f.code == "machine-noun" for f in report.warnings)


def test_plain_business_prose_carries_no_machine_noun(tmp_path):
    _write(
        tmp_path,
        "8-constraints.md",
        """# CONSTRAINTS

| Cn | Sentence | Classification |
|---|---|---|
| C1 | The kept state shall hold one entry for each declared class. | Fixed |
""",
    )
    report = record.lint_task(tmp_path)
    assert not any(f.code == "machine-noun" for f in report.warnings)


def test_render_document_syncs_the_view_by_id_and_keeps_the_prose(tmp_path):
    """The document is a VIEW of the record, keyed by id. It never holds a copy."""
    record_dir = tmp_path / "subsystems" / "alpha"
    record_dir.mkdir(parents=True)
    specs = tmp_path / "specs"
    specs.mkdir()
    _write(
        record_dir,
        "7-requirements.md",
        """# R
| Rn | EARS | Statement | Scale | Meter | Target | Verification |
|---|---|---|---|---|---|---|
| R1 | Ubiquitous | The system shall count the frames. | frames | read | 1 | test |
| R2 | Event-driven | When a frame arrives, the system shall name it. | frames | read | 1 | test |

| ACn | Rn | Check |
|---|---|---|
| AC1 | R1 | one frame, one count |
""",
    )
    _write(
        specs,
        "09-alpha.md",
        """# 09 - Alpha

Hand-written prose that must stay.

## 4. Requirements

- R1 — STALE wording that must go
  and its wrapped tail
- R2 — a second stale line

## 5. Notes

Trailing prose.
""",
    )
    first = record.render_document(record_dir, specs)
    text = (specs / "09-alpha.md").read_text(encoding="utf-8")
    assert first["changed"] is True
    assert first["rows"] == 2
    assert "- R1 — The system shall count the frames." in text
    assert "- R2 — When a frame arrives, the system shall name it." in text
    assert "STALE" not in text
    assert "wrapped tail" not in text
    assert "Hand-written prose that must stay." in text
    assert "## 5. Notes" in text and "Trailing prose." in text
    second = record.render_document(record_dir, specs)
    assert second["changed"] is False


def test_render_document_reports_an_absent_row_and_writes_nothing_new(tmp_path):
    """An id with no row in the document is reported. The document is not grown."""
    record_dir = tmp_path / "subsystems" / "alpha"
    record_dir.mkdir(parents=True)
    specs = tmp_path / "specs"
    specs.mkdir()
    _write(
        record_dir,
        "7-requirements.md",
        """# R
| Rn | EARS | Statement | Scale | Meter | Target | Verification |
|---|---|---|---|---|---|---|
| R1 | Ubiquitous | The system shall count the frames. | frames | read | 1 | test |
| R2 | Ubiquitous | The system shall name the frames. | frames | read | 1 | test |
""",
    )
    _write(specs, "09-alpha.md", "# 09 - Alpha\n\n- R1 — old wording\n")
    result = record.render_document(record_dir, specs)
    text = (specs / "09-alpha.md").read_text(encoding="utf-8")
    assert result["rows"] == 1
    assert result["absent"] == ["R2"]
    assert text == "# 09 - Alpha\n\n- R1 — The system shall count the frames.\n"


def test_goal_tree_dangling_parent_and_missing_anti_goal(tmp_path):
    _write(
        tmp_path,
        "2-goal-tree.md",
        """# GOAL TREE
| Node | Type | Statement | Refines | Disposition |
|---|---|---|---|---|
| G1 | G | top | - | top |
| G2 | R | leaf | G99 | leaf -> R1 |

| Anti-goal | Against goal | We would have failed if |
|---|---|---|
| A1 | G3 | x |
""",
    )
    report = record.lint_task(tmp_path)
    codes = {f.code for f in report.errors}
    assert "dangling-parent" in codes
    assert "top-no-anti-goal" in codes


def test_anti_goal_against_a_top_goal_passes(tmp_path):
    _write(tmp_path, "2-goal-tree.md", GOAL_OK)
    report = record.lint_task(tmp_path)
    assert not any(f.code == "top-no-anti-goal" for f in report.errors)


def test_critical_path_confirm_is_an_error(tmp_path):
    _write(
        tmp_path,
        "8-constraints.md",
        """# CONSTRAINTS
| Cn | Sentence | Class | Value | [NEEDS CONFIRM] | Critical-path? |
|---|---|---|---|---|---|
| C1 | something | Unknown | - | is it true? | yes |
""",
    )
    report = record.lint_task(tmp_path)
    assert any(f.code == "critical-confirm-open" for f in report.errors)


def test_scr_matrix_flags_a_blank_cell(tmp_path):
    _write(
        tmp_path,
        "4-mode-transition.md",
        """# MODE
Modes: M1; M2
Events: E1; E2

| mode | E1 | E2 |
|---|---|---|
| M1 | M2 |  |
| M2 | M2 | M1 |
""",
    )
    report = record.lint_task(tmp_path)
    assert any(f.code == "scr-incomplete" for f in report.errors)


def test_scr_matrix_flags_a_repeated_mode(tmp_path):
    _write(
        tmp_path,
        "4-mode-transition.md",
        """# MODE
Modes: M1; M2
Events: E1

| mode | E1 |
|---|---|
| M1 | M2 |
| M1 | M2 |
""",
    )
    report = record.lint_task(tmp_path)
    assert any(f.code == "scr-nondisjoint" for f in report.errors)


def test_scr_matrix_flags_a_missing_mode(tmp_path):
    _write(
        tmp_path,
        "4-mode-transition.md",
        """# MODE
Modes: M1; M2
Events: E1

| mode | E1 |
|---|---|
| M1 | M2 |
""",
    )
    report = record.lint_task(tmp_path)
    assert any(f.code == "scr-incomplete" for f in report.errors)


def test_scr_matrix_warns_on_an_unknown_row_and_a_column_mismatch(tmp_path):
    _write(
        tmp_path,
        "4-mode-transition.md",
        """# MODE
Modes: M1
Events: E1; E2

| mode | E1 |
|---|---|
| M9 | M1 |
""",
    )
    report = record.lint_task(tmp_path)
    codes = {f.code for f in report.warnings}
    assert "matrix-row-unknown" in codes
    assert "matrix-col-mismatch" in codes


def test_finding_carries_a_fix_hint():
    finding = record.Finding(
        record.ERROR, "fit-missing", Path("x"), 1, "R1: Target is blank"
    )
    assert "Gilb fit criterion" in finding.render()


def test_traceability_orphan_and_missing(tmp_path):
    _write(
        tmp_path,
        "7-requirements.md",
        """# R
| Rn | EARS | Statement | Scale | Meter | Target | Verification |
|---|---|---|---|---|---|---|
| R1 | Ubiquitous | s | s | m | 1 | test |

| ACn | Rn | Check |
|---|---|---|
| AC1 | R1 | ok |
""",
    )
    _write(
        tmp_path,
        "11-traceability.md",
        """# TRACE
| Rn | Goal | Test |
|---|---|---|
| R9 | G1 | t |
""",
    )
    report = record.lint_task(tmp_path)
    codes = {f.code for f in report.errors}
    assert "trace-orphan" in codes
    assert "trace-missing" in codes


def test_a_traceability_row_without_a_test_is_an_error(tmp_path):
    """A requirement may not settle without a named test."""
    _write(
        tmp_path,
        "7-requirements.md",
        """# R
| Rn | EARS | Statement | Scale | Meter | Target | Verification |
|---|---|---|---|---|---|---|
| R1 | Ubiquitous | s | s | m | 1 | test |

| ACn | Rn | Check |
|---|---|---|
| AC1 | R1 | ok |
""",
    )
    _write(
        tmp_path,
        "11-traceability.md",
        """# TRACE
| Rn | Goal | Test |
|---|---|---|
| R1 | G1 | - |
""",
    )
    report = record.lint_task(tmp_path)
    assert [f.code for f in report.errors] == ["trace-no-test"]
    assert not report.passed()


def test_spec_number_duplicate_and_gap_are_warnings(tmp_path):
    """A repeated number and a hole in the sequence are both reported."""
    specs = tmp_path / "specs"
    specs.mkdir()
    _write(specs, "04-x.md", "- R1 — a\n- R1 — b\n")
    report = record.lint_task(tmp_path / "subsystems" / "x", specs)
    assert any(f.code == "spec-number-duplicate" for f in report.warnings)
    _write(specs, "05-y.md", "- R1 — a\n- R3 — c\n")
    report = record.lint_task(tmp_path / "subsystems" / "y", specs)
    assert any(f.code == "spec-number-gap" for f in report.warnings)


def test_record_requirements_file_is_linted(tmp_path):
    """The record projection uses requirements.md, not 7-requirements.md."""
    _write(
        tmp_path,
        "requirements.md",
        """# REQUIREMENTS
| Rn | EARS | Statement | Scale | Meter | Target | Verification | Refines |
|---|---|---|---|---|---|---|---|
| R1 | Ubiquitous | the system shall do a thing | s | m | 1 | test | G1.1 |
""",
    )
    report = record.lint_task(tmp_path)
    assert any(f.code == "rn-no-acn" for f in report.errors)


def test_empty_directory_warns(tmp_path):
    report = record.lint_task(tmp_path)
    assert any(f.code == "no-record" for f in report.warnings)


def test_obstacle_without_a_resolution_is_an_error(tmp_path):
    _write(
        tmp_path,
        "10-obstacles-misuse-unknowns.md",
        """# 10
| O# | Obstructs (goal) | Condition | Resolution (Rn / Xn / —) |
|---|---|---|---|
| O1 | G1 | something | — |
""",
    )
    report = record.lint_task(tmp_path)
    assert any(f.code == "obstacle-undischarged" for f in report.errors)


def test_obstacle_resolved_by_a_decision_passes(tmp_path):
    _write(
        tmp_path,
        "10-obstacles-misuse-unknowns.md",
        """# 10
| O# | Obstructs (goal) | Condition | Resolution (Rn / Xn / —) |
|---|---|---|---|
| O1 | G1 | something | D3 (pending the gate) |
""",
    )
    report = record.lint_task(tmp_path)
    assert not any(f.code == "obstacle-undischarged" for f in report.errors)


def test_event_table_with_two_when_values_for_one_pair_is_an_error(tmp_path):
    _write(
        tmp_path,
        "5-event.md",
        """# 5
| Event | Condition | When | Response |
|---|---|---|---|
| E1 | the moment is older | @T | ignore |
| E1 | the moment is older | @F | accept |
""",
    )
    report = record.lint_task(tmp_path)
    assert any(f.code == "event-ambiguous" for f in report.errors)


def test_event_when_shape_warns(tmp_path):
    _write(
        tmp_path,
        "5-event.md",
        """# 5
| Event | Condition | When | Response |
|---|---|---|---|
| E1 | c | always | x |
""",
    )
    report = record.lint_task(tmp_path)
    assert any(f.code == "event-when-shape" for f in report.warnings)


def test_open_decision_is_a_warning_not_a_failure(tmp_path):
    _write(
        tmp_path,
        "decisions.md",
        """# DECISIONS
| Dn | Instrument | Question | Options | Operator answer |
|---|---|---|---|---|
| D1 | Myers | q | a · b |  |
""",
    )
    report = record.lint_task(tmp_path)
    assert any(f.code == "decision-open" for f in report.warnings)
    assert report.passed()


def _module_skeleton(tmp_path, *rows: str):
    """A module skeleton under modules/<m>/ — the contract home."""
    module = tmp_path / "subsystems" / "alpha" / "modules" / "core"
    module.mkdir(parents=True)
    text = (
        "# SKELETON\n\n"
        "| Method (signature) | Pre | Post | Invariant | CQS | Responsibility |\n"
        "|---|---|---|---|---|---|\n" + "\n".join(rows) + "\n"
    )
    _write(module, "SKELETON.md", text)
    return module


def test_module_skeleton_contracts_are_linted(tmp_path):
    """The module SKELETON.md is the contract home, so its table is linted."""
    module = _module_skeleton(
        tmp_path, "| `A.run(self) -> None` | - | ok | - | - | Run. |"
    )
    report = record.lint_task(module)
    assert any(f.code == "cqs-count" for f in report.warnings)


def test_module_skeleton_blank_contract_row_warns(tmp_path):
    """A method row with a blank pre and post is a finding, not noise."""
    module = _module_skeleton(
        tmp_path, "| `A.run(self) -> None` | - | - | - | Q | Run. |"
    )
    report = record.lint_task(module)
    assert any(f.code == "contract-blank" for f in report.warnings)


def test_the_generated_union_skeleton_is_not_linted(tmp_path):
    """The union SKELETON.md at the root concatenates modules, so it is skipped."""
    _write(
        tmp_path,
        "SKELETON.md",
        "# SKELETON\n\n<!-- GENERATED by swarm.genRecord -->\n\n"
        "| Method (signature) | Pre | Post | Invariant | CQS | Responsibility |\n"
        "|---|---|---|---|---|---|\n"
        "| `A.run(self) -> None` | - | ok | - | - | Run. |\n",
    )
    report = record.lint_task(tmp_path)
    assert not any(f.code == "cqs-count" for f in report.warnings)
