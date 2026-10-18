"""Tests for the interrogator's forms and the harness check/init-work surface.

The role writes its section files directly; these tests cover the guidelines
(the forms and the method map) and the linter over what was written.
"""

import json
from pathlib import Path

import pytest
import questions


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


def test_the_spec_has_the_method_sections():
    files = [section.file for section in questions.INTERROGATOR.sections]
    for expected in (
        "00-header.md",
        "0-frame.md",
        "4-mode-transition.md",
        "7-requirements.md",
        "decisions.md",
        "13-record-note.md",
    ):
        assert expected in files


def test_emit_templates_writes_the_forms(tmp_path):
    """A form carries its heading and its field names, and no copy of the method."""
    written = questions.emit_templates(questions.INTERROGATOR, tmp_path)
    assert len(written) == len(questions.INTERROGATOR.sections)
    requirements = (tmp_path / "7-requirements.md").read_text(encoding="utf-8")
    assert "| Rn |" in requirements
    assert "| ACn |" in requirements
    assert "> Rule:" not in requirements


def test_the_method_lives_in_the_guide_and_not_in_the_form():
    """The method stays in the spec once. A record never holds a copy of it."""
    section = next(
        s for s in questions.INTERROGATOR.sections if s.file == "7-requirements.md"
    )
    assert any(hasattr(part, "markdown") for part in section.parts)
    emitted = questions._render_form(section)
    assert "> Rule:" not in emitted
    assert "> Instrument:" not in emitted
    assert "| Rn |" in emitted


def test_render_stop_test_reports_errors_and_warnings():
    import record

    passing = record.Report()
    assert questions.render_stop_test(passing).startswith("pass")
    warning = record.Report()
    warning.warn("decision-open", Path("x"), 1, "open")
    assert "warning" in questions.render_stop_test(warning)
    failing = record.Report()
    failing.error("fit-missing", Path("x"), 2, "blank")
    assert questions.render_stop_test(failing).startswith("fail")


def test_init_work_writes_the_flat_record(tmp_path):
    import harness

    work = tmp_path / "w"
    harness.main(
        [
            "--config",
            str(_cfg(tmp_path)),
            "init-work",
            "interrogator",
            "--work",
            str(work),
        ]
    )
    assert (work / "requirements.md").is_file()
    text = (work / "requirements.md").read_text(encoding="utf-8")
    assert "| Rn |" in text
    assert "> Rule:" not in text


def test_check_passes_a_minimal_written_record(tmp_path, capsys):
    import harness

    work = tmp_path / "w"
    work.mkdir()
    (work / "requirements.md").write_text(
        "# REQUIREMENTS\n"
        "| Rn | EARS | Statement | Scale | Meter | Target | Verification |\n"
        "|---|---|---|---|---|---|---|\n"
        "| R1 | Ubiquitous | The system shall name its outcome YES or NO. | words | read it | 2 | inspection |\n\n"
        "| ACn | Rn | Check |\n|---|---|---|\n| AC1 | R1 | 2 words |\n",
        encoding="utf-8",
    )
    with pytest.raises(SystemExit) as exit_info:
        harness.main(
            [
                "--config",
                str(_cfg(tmp_path)),
                "check",
                "interrogator",
                "--work",
                str(work),
            ]
        )
    assert exit_info.value.code == 0
    assert "STOP TEST" in capsys.readouterr().out


def test_check_flags_a_defect_in_the_written_record(tmp_path):
    import harness

    work = tmp_path / "w"
    work.mkdir()
    (work / "requirements.md").write_text(
        "# REQUIREMENTS\n"
        "| Rn | EARS | Statement | Scale | Meter | Target | Verification |\n"
        "|---|---|---|---|---|---|---|\n"
        "| R1 | Ubiquitous, When x | s | s | m |  | test, inspection |\n",
        encoding="utf-8",
    )
    with pytest.raises(SystemExit) as exit_info:
        harness.main(
            [
                "--config",
                str(_cfg(tmp_path)),
                "check",
                "interrogator",
                "--work",
                str(work),
            ]
        )
    assert exit_info.value.code == 2


def test_guide_prints_the_method_map(capsys):
    import argparse

    import harness

    class FakePaths:
        def pack_root(self):
            return Path("/pack")

    harness.cmd_guide(
        argparse.Namespace(role="interrogator", subsystem="t"), FakePaths()
    )
    out = capsys.readouterr().out
    assert "HOW YOU WORK" in out
    assert "init-work interrogator" in out
    assert "requirements.md" in out
