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
    "ANTI_GOALS",
    "FLAT_FILES",
    "FLAT_SECTIONS",
    "GOAL_TREE",
    "INTERROGATOR",
    "ROLE_TOOLS",
    "SPECS",
    "STOP_TESTS",
    "Column",
    "Computed",
    "Field",
    "Matrix",
    "RoleSpec",
    "Section",
    "Table",
    "Text",
    "_c",
    "_render_form",
    "emit_flat",
    "emit_templates",
    "has_work_dir",
    "render_stop_test",
    "work_dir_for",
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

# The four roles that own a file in the design record.
DESIGN_ROLES: tuple[str, ...] = ("interrogator", "architect", "designer", "critic")


def has_work_dir(role: str) -> bool:
    """True when the role has a file in the design record."""
    return role in DESIGN_ROLES


def work_dir_for(role: str, root=None) -> str:
    """The work directory of a role. Empty means the subsystem root.

    The record is flat: requirements.md, architecture.md and review.md at the
    root, and one modules/<module>.md per module. A designer works in modules/.
    """
    if role == "designer":
        return "modules"
    return ""


# The one-line pass condition of each role's stop test. `reference/design-quality.md`
# holds the full, authoritative definition; the design envelope carries this line and
# never the whole section.
ROLE_TOOLS: dict[str, str] = {
    "orchestrator": "envelope, goal, status, modules, interface, ready, decisions, guide, subagent",
    "interrogator": "status, guide, initWork, check, genDoc, decisions",
    "specifier": "status, guide, gherkinParse, gherkinDry, ready",
    "architect": "status, guide, modules, interface, uml, check, genRecord",
    "designer": "status, guide, interface, uml, check",
    "critic": "status, modules, interface, uml, genRecord, check",
    "coder": "status, guide, pytest, acceptance, ruff",
    "test-reviewer": "status, guide, pytest",
    "refactorer": "status, gate, crap, dry, uml, pytest",
    "hotfixer": "status, ruff, pytest, acceptance, lintRecord",
}

STOP_TESTS: dict[str, str] = {
    "interrogator": "each Rn has one EARS pattern, Scale/Meter/Target, one verification, and one ACn; each ACn names an Rn; each Cn has a class; each Xn has a reason; each Rn has a traceability row that names its test; zero open decisions; the spec document matches the record.",
    "architect": "write sets are disjoint; the graph is acyclic; one secret per module; every shared edge has a frozen interface section in architecture.md; every acceptance check crosses a declared interface; zero model violations; zero open decisions.",
    "designer": "every method has pre, post, invariant, and one CQS tag; every acceptance check has a named test wired to a signature; every OCP seam is built or has a YAGNI reason; no duplicated policy; zero open decisions; every frozen interface is honored.",
    "critic": "no implementer violates a frozen interface; no interface method is unused by every client; zero duplicated policy across modules; every module earns its keep; SKELETON.md is generated; zero model violations; zero open decisions.",
    "specifier": "the parser and the dry-checker exit 0; every Rn has a scenario; the operator approved.",
    "coder": "the chunk test was red for the right reason, then green; ruff is clean; the acceptance step runs; every twin is updated; no comment and no docstring.",
    "test-reviewer": "two runs recorded; every accepted test has an oracle, an isolation argument, and a mutation target; no over-mocking; a verdict is given.",
    "refactorer": "CRAP is at most 10 per function; dry, ruff, format, pytest, and acceptance pass; model.html is refreshed; no behavior changed.",
    "hotfixer": "the defect reproduces red, then green; every twin is fixed; pytest, acceptance, and ruff pass; no requirement, contract, or scenario shape changed.",
}


# --------------------------------------------------------------------------- #
# Composition roots used by harness.py
# --------------------------------------------------------------------------- #


FLAT_FILES = {
    "interrogator": "requirements.md",
    "architect": "architecture.md",
    "critic": "review.md",
}

FLAT_HEADERS = {
    "interrogator": (
        "# REQUIREMENTS — <subsystem>\n\n"
        "REQUEST: <the ask, verbatim>\n\n"
        "DRAFT: <document path, or none>\n\n"
        "SPEC: docs/specs/NN-<subsystem>.md — refined or created\n"
    ),
    "architect": "# ARCHITECTURE — <subsystem>\n\nFROZEN FROM REQUIREMENTS: goal, constraints, exclusions.\n",
    "critic": "# REVIEW — <subsystem>\n\nFROZEN FROM DESIGNERS: contracts and test map.\n",
}

FLAT_SECTIONS = {
    "interrogator": (
        "0-frame.md",
        "1-goal.md",
        "7-requirements.md",
        "8-constraints.md",
        "9-exclusions.md",
        "11-traceability.md",
        "decisions.md",
    ),
}

FLAT_ARCHITECTURE = """
## MODULES

| Module | Owns | Provides | Requires | Secret |
|---|---|---|---|---|
| | | | | |

## SHARED FILES

| File | Modules that edit it | Order |
|---|---|---|
| | | |

## ACCEPTANCE WALK

| Acceptance check | Modules crossed | Interface |
|---|---|---|
| | | |

## DECISIONS

| Dn | Question | Options | Answer |
|---|---|---|---|
| | | | |
"""

FLAT_REVIEW = """
## EXTENSION

<what a new behavior must edit, and what it must not>

## SUBSTITUTABILITY

<LSP and ISP across the frozen interfaces>

## ECONOMY

<duplication, caller closure, naming>

## TRIM

<YAGNI and the scope gate answer>

## CROSS-MODULE BRIEF

<the one brief the coder needs>

## DECISIONS

| Dn | Question | Options | Answer |
|---|---|---|---|
| | | | |
"""

FLAT_INTERFACES = """
## Interface <module>

- Provides: <signatures the module offers>
- Requires: <signatures it needs>
- Consumers: <modules that call it>
- Shared files: <files this module edits, with the order>
"""

FLAT_MODULE = """# MODULE — <module>

## Contract

| Method (signature) | Pre | Post | Invariant | CQS | Responsibility |
|---|---|---|---|---|---|
| | | | | | |

## Design

- Responsibility: <one sentence>
- Seams: <ports, adapters, OCP>
- Test map: <acceptance check -> test -> method>
- Frozen interface honored: yes/no

## Decisions

| Dn | Question | Answer |
|---|---|---|
| | | |
"""


def emit_flat(role: str, root: Path, module: str | None = None) -> list[Path]:
    """Write one flat record file for a role, or one module contract.

    The old forms stay available through `guide`, but a new subsystem does not
    persist them. Scratch analysis is not a deliverable. The facts that
    downstream roles and the linters need live in four files.
    """
    root.mkdir(parents=True, exist_ok=True)
    if role == "designer":
        mod_dir = root / "modules"
        mod_dir.mkdir(parents=True, exist_ok=True)
        path = mod_dir / f"{module or 'module'}.md"
        path.write_text(FLAT_MODULE, encoding="utf-8")
        return [path]
    if role not in FLAT_FILES:
        return []
    wanted = set(FLAT_SECTIONS.get(role, ()))
    spec = SPECS.get(role)
    parts = []
    if spec is not None:
        parts = [
            _render_form(section) for section in spec.sections if section.file in wanted
        ]
    elif role == "architect":
        parts = [FLAT_ARCHITECTURE]
    elif role == "critic":
        parts = [FLAT_REVIEW]
    if role == "architect":
        parts.append(FLAT_INTERFACES)
    parts.insert(0, FLAT_HEADERS.get(role, ""))
    path = root / FLAT_FILES[role]
    path.write_text(
        "\n\n".join(part.rstrip() for part in parts) + "\n", encoding="utf-8"
    )
    return [path]


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
    written here. The guide carries it once (`swarm.guide`), so one
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
