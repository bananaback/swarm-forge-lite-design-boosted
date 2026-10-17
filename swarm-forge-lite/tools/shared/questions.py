"""forms -- the design forms and the method's map (guidelines, not a driver).

The role writes its section files directly with its own editor. This subsystem holds
the shape of the interrogator's forms (so `guide` can list them) and the
self-teaching blank forms that `init-work` writes to WORK, plus the numbered work
directory and the one-line stop-test pass condition of every role. `check` lints
what the role wrote; nothing here renders, records, or answers anything.
"""

from __future__ import annotations

from pathlib import Path

from questions_engine import (
    Column,
    Computed,
    Field,
    Matrix,
    RoleSpec,
    Section,
    Table,
    Text,
    _c,
    render_stop_test,
)
from questions_interrogator_a import (
    ANTI_GOALS,
    GOAL_TREE,
    _interrogator_sections_a,
)
from questions_interrogator_b import _interrogator_sections_b

__all__ = [
    'ANTI_GOALS',
    'DESIGN_ROLES',
    'GOAL_TREE',
    'INTERROGATOR',
    'NOTE_DIRS',
    'SPECS',
    'STOP_TESTS',
    'WORK_DIRS',
    'Column',
    'Computed',
    'Field',
    'Matrix',
    'RoleSpec',
    'Section',
    'Table',
    'Text',
    '_c',
    '_render_form',
    'emit_templates',
    'has_work_dir',
    'load_spec',
    'render_stop_test',
    'work_dir_for',
]


def _interrogator_sections() -> tuple[Section, ...]:
    return _interrogator_sections_a() + _interrogator_sections_b()


INTERROGATOR = RoleSpec(
    "interrogator",
    "01-interrogator",
    _interrogator_sections(),
)


SPECS: dict[str, RoleSpec] = {
    INTERROGATOR.role: INTERROGATOR,
}

# The canonical numbered work directory of each design role. The number orders the
# roles; the tool and the protocol use the same name.
WORK_DIRS: dict[str, str] = {
    "interrogator": "01-interrogator",
    "architect": "02-architect",
    "designer": "modules",
    "critic": "04-critic",
}
DESIGN_ROLES: tuple[str, ...] = ("interrogator", "architect", "designer", "critic")

# The two build roles that may keep a note in the record. Every other build role
# writes to the source and test roots, so it has no record directory. One list, so
# `envelope` and `guide` never disagree about which roles have a `WORK` path.
NOTE_DIRS: tuple[str, ...] = ("specifier", "coder")


def has_work_dir(role: str) -> bool:
    """True when the role has a directory in the design record."""
    return role in WORK_DIRS or role in NOTE_DIRS


def work_dir_for(role: str) -> str:
    """The work directory name of a role (numbered for the design roles)."""
    return WORK_DIRS.get(role, role)


# The one-line pass condition of each role's stop test. `reference/design-quality.md`
# holds the full, authoritative definition; the design envelope carries this line and
# never the whole section.
STOP_TESTS: dict[str, str] = {
    "interrogator": "SCR completeness and disjointness; every event x condition resolves to one value; one agent satisfies every goal leaf; 0 undischarged obstacles; every top goal has an anti-goal; each requirement has one EARS pattern, Scale/Meter/Target, and one verification; no blank constraint class; no critical-path [NEEDS CONFIRM]; the requirement document exists and matches the record.",
    "architect": "a second grammar pass adds 0 entries; every acceptance check walks card-to-card with no gap; no card has 0 responsibilities; one secret per card; no Core -> concrete-Shell edge; the graph is acyclic; no SRP sentence contains 'and'; every sequence-shaped check names a state owner; the boundary map is frozen: write sets disjoint, acyclic, every shared edge frozen, every shared file named.",
    "designer": "every method has pre/post/invariant and exactly one CQS tag; no call chain exceeds one dot past self/param/local; every acceptance check has a named test wired to a signature; every OCP seam is built or has a YAGNI reason; no implementer violates a contract; no interface method is unused by every client; 0 duplicated policy; 0 classes outside the caller closure; every name is self-explanatory with its contract alone; the module honors every frozen interface.",
    "critic": "at least one exclusion slots in by addition or has a YAGNI reason; no implementer violates a contract; no interface method is unused by every client; 0 duplicated policy across the modules; 0 classes outside the caller closure; every name is self-explanatory with its contract alone; every module honored its frozen interface; the subsystem SKELETON is the union with no cross-module duplication.",
    "specifier": "the parser and the dry-checker exit 0 on the feature; every Rn has a scenario; the operator approved.",
    "coder": "the pinned test of the chunk and the acceptance of its feature are green.",
    "test-reviewer": "every test has a real oracle, is isolated, and is mutation-honest; the verdict and the findings file are present.",
    "refactorer": "DRY, ruff, the full persistent suite, and the acceptance runner are green; the diagram is refreshed.",
    "hotfixer": "the defect reproduces red, the fix is green, and every touched layer is updated.",
}


# --------------------------------------------------------------------------- #
# Composition roots used by harness.py
# --------------------------------------------------------------------------- #


def load_spec(role: str) -> RoleSpec:
    if role not in SPECS:
        raise KeyError(f"no question spec for role: {role}")
    return SPECS[role]


def emit_templates(spec: RoleSpec, template_dir: Path) -> list[Path]:
    """Write the empty, self-teaching forms for a role (the guidelines to fill)."""
    template_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for section in spec.sections:
        path = template_dir / section.file
        path.write_text(_render_form(section), encoding="utf-8")
        written.append(path)
    return written


def _render_form(section: Section) -> str:
    """The section file: the heading and the field names alone.

    The method - the prose, the instrument and the rule of each part - is NOT
    written here. The guide carries it once (`swarm.guide`, `swarm.form`), so one
    method serves every record, and no record holds a copy of it.
    """
    lines = [f"## {section.title}", ""]
    for part in section.parts:
        if isinstance(part, Text):
            lines += [part.markdown.rstrip(), ""]
        if isinstance(part, Field):
            lines += [f"{part.label} {part.template}".rstrip(), ""]
        elif isinstance(part, Table):
            lines += [
                "| " + " | ".join(c.header() for c in part.columns) + " |",
                "|" + "|".join("---" for _ in part.columns) + "|",
                "| " + " | ".join("" for _ in part.columns) + " |",
                "",
            ]
        elif isinstance(part, Matrix):
            lines += [
                f"| {part.row_label} | <keys of {part.columns_from}> |",
                "|---|---|",
                "| | |",
                "",
            ]
        elif isinstance(part, Computed):
            lines += [f"> {part.label} computed by `check`.", ""]
    return "\n".join(lines).rstrip() + "\n"
