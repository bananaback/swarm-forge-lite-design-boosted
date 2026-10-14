"""forms -- the design forms and the method's map (guidelines, not a driver).

The role writes its section files directly with its own editor. This subsystem holds
the shape of the interrogator's forms (so `guide` can list them) and the
self-teaching blank forms that `init-work` writes to WORK, plus the numbered work
directory and the one-line stop-test pass condition of every role. `check` lints
what the role wrote; nothing here renders, records, or answers anything.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import record


@dataclass(frozen=True)
class Column:
    key: str
    label: str
    prompt: str = ""

    def header(self) -> str:
        return self.label


@dataclass(frozen=True)
class Text:
    """Static markdown between the fillable cells."""

    markdown: str


@dataclass(frozen=True)
class Field:
    """One free-text answer: a labelled line."""

    item_id: str
    label: str
    prompt: str
    instrument: str = ""
    template: str = ""
    rule: str = ""

    def is_filled(self, answers: dict) -> bool:
        value = answers.get(self.item_id)
        return bool(value and str(value).strip())


@dataclass(frozen=True)
class Table:
    """A repeatable table: one answer is one row (a dict of column values)."""

    item_id: str
    columns: tuple[Column, ...]
    prompt: str
    instrument: str = ""
    min_rows: int = 1
    repeatable: bool = True
    rule: str = ""

    @property
    def key_column(self) -> str:
        """The first column is the row's natural key (upsert target)."""
        return self.columns[0].key if self.columns else ""

    def rows(self, answers: dict) -> list[dict]:
        value = answers.get(self.item_id) or []
        return list(value)

    def is_filled(self, answers: dict) -> bool:
        return len(self.rows(answers)) >= self.min_rows


@dataclass(frozen=True)
class Matrix:
    """A table whose columns come from another answer's list (modes x events)."""

    item_id: str
    row_label: str
    columns_from: str
    prompt: str
    instrument: str = ""
    column_prompt: str = ""
    min_rows: int = 1
    rule: str = ""

    @property
    def key_column(self) -> str:
        return self.row_label.lower().replace(" ", "_")

    def rows(self, answers: dict) -> list[dict]:
        return list(answers.get(self.item_id) or [])

    def is_filled(self, answers: dict) -> bool:
        return len(self.rows(answers)) >= self.min_rows

    def column_keys(self, answers: dict) -> list[str]:
        raw = answers.get(self.columns_from) or []
        if isinstance(raw, str):
            raw = re.split(r"[;\n]", raw)
        keys: list[str] = []
        for entry in raw:
            entry = str(entry).strip()
            if not entry:
                continue
            keys.append(
                entry.split()[0] if re.match(r"^[A-Za-z]+[0-9]", entry) else entry
            )
        return keys


@dataclass(frozen=True)
class Computed:
    """A cell the harness fills from a check (the stop-test counts)."""

    item_id: str
    label: str
    renderer: Callable[[record.Report], str]


Item = Field | Table | Matrix | Computed


@dataclass(frozen=True)
class Section:
    order: int
    file: str
    title: str
    parts: tuple[Text | Item, ...]

    def items(self) -> list[Item]:
        return [part for part in self.parts if not isinstance(part, Text)]


@dataclass(frozen=True)
class RoleSpec:
    role: str
    work_dir: str
    sections: tuple[Section, ...]

    def items(self) -> list[tuple[Section, Item]]:
        out: list[tuple[Section, Item]] = []
        for section in self.sections:
            for item in section.items():
                out.append((section, item))
        return out

    def find(self, item_id: str) -> tuple[Section, Item]:
        for section, item in self.items():
            if item.item_id == item_id:
                return section, item
        raise KeyError(item_id)


# --------------------------------------------------------------------------- #
# Answer store
# --------------------------------------------------------------------------- #


def render_stop_test(report: record.Report | None) -> str:
    if report is None:
        return "(render + check first)"
    errors = sorted({f.code for f in report.errors})
    warnings = sorted({f.code for f in report.warnings})
    open_decisions = sum(1 for f in report.warnings if f.code == "decision-open")
    parts = [
        f"{len(report.errors)} error(s)" + (f": {', '.join(errors)}" if errors else "")
    ]
    parts.append(
        f"{len(report.warnings)} warning(s)"
        + (f": {', '.join(warnings)}" if warnings else "")
    )
    if open_decisions:
        parts.append(f"{open_decisions} decision(s) open at the gate")
    return ("fail — " if report.errors else "pass — ") + "; ".join(parts)


# --------------------------------------------------------------------------- #
# Progress
# --------------------------------------------------------------------------- #


def _c(key: str, label: str, prompt: str = "") -> Column:
    return Column(key, label, prompt)


GOAL_TREE = Table(
    "2-goal-tree.goals",
    (
        _c("node", "Node", "G1, G1.1, ..."),
        _c(
            "type",
            "Type (G/R/O/A/X)",
            "G goal, R requirement leaf, O obstacle, A anti-goal, X exclusion",
        ),
        _c("statement", "Statement", "the goal in one sentence"),
        _c("refines", "Refines (parent)", "the parent node id, or — for a top goal"),
        _c("disposition", "Disposition", "AND / OR / leaf -> Rn / excluded"),
    ),
    "Add one goal-tree row per node: refine AND/OR until every leaf is satisfiable by one agent.",
    instrument="KAOS refinement (Dardenne, van Lamsweerde, Fickas, 1993)",
    min_rows=1,
    rule="every leaf is satisfiable by one agent; Refines names a declared node; one anti-goal per top goal",
)

ANTI_GOALS = Table(
    "2-goal-tree.anti-goals",
    (
        _c("anti_goal", "Anti-goal", "A1, A2, ..."),
        _c("against", "Against goal", "the top goal it negates, G1"),
        _c("failed_if", "We would have failed if", "the observable failure"),
    ),
    "Add one anti-goal per top goal.",
    instrument="KAOS anti-goals",
    min_rows=1,
    rule="every top goal is named in the Against goal column",
)


def _interrogator_sections() -> tuple[Section, ...]:
    return (
        Section(
            0,
            "00-header.md",
            "interrogator work — <subsystem>",
            (
                Text(
                    "SUBSYSTEM: design/subsystems/<subsystem>/01-interrogator/\n"
                    "Methods: `<pack>/reference/design-craft-front.md`, "
                    "`<pack>/reference/design-quality.md`. "
                    "A cell you cannot fill is a finding, not a blank."
                ),
                Field(
                    "00-header.req",
                    "REQUEST:",
                    "the ask verbatim, copied from the dispatch",
                ),
                Field(
                    "00-header.draft", "DRAFT:", "the draft requirement path, or `none`"
                ),
                Field(
                    "00-header.spec",
                    "SPEC:",
                    "docs/specs/NN-<subsystem>.md — `refined` or `created`",
                ),
            ),
        ),
        Section(
            0,
            "0A-spec.md",
            "0A. SPEC — the requirement document",
            (
                Text(
                    "Resolve the requirement document before framing. Refine an existing draft to "
                    "match the accepted record; create the doc when none exists. House shape: "
                    "`# NN — <name>`, then Purpose · Scope (in/out) · Definitions · Requirements "
                    "(`- Rn — <statement>`) · Acceptance Criteria (`- ACn — <check>`) · Constraints. "
                    "One-to-one with the record's Rn/ACn. Business vocabulary only: no token in "
                    "code marks, no path, no file name, no class or element name, no framework or "
                    "library name. A class name and a path belong to the design record alone."
                ),
                Field(
                    "0A-spec.draft",
                    "Draft read:",
                    "what the draft says (or `none`), one line",
                ),
                Field(
                    "0A-spec.decision",
                    "Decision:",
                    "`refined` or `created`, and the path",
                ),
                Field(
                    "0A-spec.changes",
                    "Decisions on the doc:",
                    "one line per change, or `created`",
                ),
            ),
        ),
        Section(
            0,
            "0-frame.md",
            "0. FRAME — requirement, not design",
            (
                Text(
                    "Describe the world outside the machine. The perfect-technology filter asks what "
                    "must be true if the machine were free and instantaneous. Name no machine noun: "
                    "no token in code marks, no path, no class or element name, no framework name."
                ),
                Field(
                    "0-frame.client",
                    "Real client:",
                    "who decides, separately from who asks",
                ),
                Field(
                    "0-frame.success",
                    "Definition of success:",
                    "what would make them say it worked",
                ),
                Field(
                    "0-frame.world",
                    "The world that must change:",
                    "phenomena outside the machine",
                ),
                Table(
                    "0-frame.context-free",
                    (
                        _c(
                            "question",
                            "Context-free question (Gause & Weinberg)",
                            "fixed",
                        ),
                        _c(
                            "answer",
                            "Answer, or `[NEEDS CONFIRM]`",
                            "the owner if it cannot be answered",
                        ),
                    ),
                    "Answer each context-free question; an unanswered one is `[NEEDS CONFIRM]` with an owner.",
                    instrument="Gause & Weinberg (1989) context-free questions",
                    min_rows=4,
                    repeatable=False,
                ),
                Table(
                    "0-frame.leaks",
                    (
                        _c(
                            "leaked",
                            "Sentence that leaked design",
                            "a sentence naming how, not what",
                        ),
                        _c(
                            "sent_back",
                            "Sent back as",
                            "the same behaviour with the machine free",
                        ),
                    ),
                    "One row per design sentence found in the ask; empty the table by rewriting each.",
                    instrument="perfect-technology filter (McMenamin & Palmer, 1984)",
                    min_rows=0,
                ),
            ),
        ),
        Section(
            0,
            "1-goal.md",
            "1. GOAL — fit criterion (Gilb)",
            (
                Text("The measurable goal. Reject every unmeasurable verb."),
                Field(
                    "1-goal.statement",
                    "Goal:",
                    "When <trigger>, the system shall <outcome>, verified by <observable check>.",
                ),
                Field("1-goal.scale", "Scale:", "what is measured"),
                Field("1-goal.meter", "Meter:", "how it is measured"),
                Field("1-goal.target", "Target:", "the number or state that must hold"),
                Field(
                    "1-goal.rejected",
                    "Unmeasurable verbs found and rejected:",
                    "the list, or `none`",
                ),
            ),
        ),
        Section(
            0,
            "2-goal-tree.md",
            "2. GOAL TREE — KAOS refinement",
            (
                Text(
                    "Refine AND/OR until every leaf is satisfiable by one agent — that leaf is a requirement."
                ),
                GOAL_TREE,
                Text("Every top goal carries one anti-goal."),
                ANTI_GOALS,
                Field(
                    "2-goal-tree.notes",
                    "Notes:",
                    "the refinement note: why every leaf is satisfiable by one agent",
                ),
            ),
        ),
        Section(
            0,
            "3-variables.md",
            "3. VARIABLES — the four-variable model (SCR)",
            (
                Text(
                    "A requirement relates monitored and controlled variables only — never internals."
                ),
                Field(
                    "3-variables.monitored",
                    "Monitored (env → system):",
                    "the variables the world gives the system",
                ),
                Field(
                    "3-variables.controlled",
                    "Controlled (system → env):",
                    "the variables the system changes in the world",
                ),
                Field(
                    "3-variables.input",
                    "Input (internal, derived):",
                    "derived, never named in a requirement",
                ),
                Field(
                    "3-variables.output",
                    "Output (internal, derived):",
                    "derived, never named in a requirement",
                ),
            ),
        ),
        Section(
            0,
            "4-mode-transition.md",
            "4. MODE TRANSITION TABLE (SCR)",
            (
                Text(
                    "`@` = any. Completeness: every mode × event has one entry. Disjointness: none has two."
                ),
                Field(
                    "4-mode-transition.modes",
                    "Modes:",
                    "semicolon-separated (`;`), M1 name; M2 name; ...",
                ),
                Field(
                    "4-mode-transition.events",
                    "Events:",
                    "semicolon-separated (`;`), E1 name; E2 name; ...",
                ),
                Matrix(
                    "4-mode-transition.rows",
                    "mode",
                    "4-mode-transition.events",
                    "One row per mode: the next mode for every event.",
                    instrument="Parnas SCR mode transition (1978)",
                    column_prompt="the next mode, or `@`",
                    rule="every mode × event cell has exactly one entry; each mode appears once",
                ),
                Field(
                    "4-mode-transition.notes",
                    "Notes:",
                    "the completeness and disjointness note, and any derivation prose",
                ),
            ),
        ),
        Section(
            0,
            "5-event.md",
            "5. EVENT TABLE (SCR)",
            (
                Text(
                    "`@T` when a condition becomes true · `@F` when it becomes false · `@C` when it changes."
                ),
                Table(
                    "5-event.events",
                    (
                        _c("event", "Event", "E1, E2, ..."),
                        _c("condition", "Condition", "the condition the event reads"),
                        _c("when", "When", "@T / @F / @C"),
                        _c(
                            "response",
                            "Response",
                            "the response, naming its requirements",
                        ),
                    ),
                    "One row per event; each (event, condition) resolves to exactly one When value.",
                    instrument="Parnas SCR event table",
                    min_rows=1,
                    rule="one row per event; each (event, condition) resolves to exactly one When "
                    "value (@T / @F / @C; `@` = any)",
                ),
                Field(
                    "5-event.notes",
                    "Notes:",
                    "any derivation prose for the event table",
                ),
            ),
        ),
        Section(
            0,
            "6-condition.md",
            "6. CONDITION TABLE (SCR)",
            (
                Text(
                    "Condition × mode → T/F. The columns are the modes from `4-mode-transition.modes`."
                ),
                Field(
                    "6-condition.conditions",
                    "Conditions:",
                    "semicolon-separated (`;`), K1 name; K2 name; ...",
                ),
                Matrix(
                    "6-condition.rows",
                    "condition",
                    "4-mode-transition.modes",
                    "One row per condition: its truth in every mode (a mode key per cell).",
                    instrument="Parnas SCR condition table",
                    rule="every condition × mode cell resolves to exactly one value; each condition once",
                ),
                Field(
                    "6-condition.notes",
                    "Notes:",
                    "any derivation prose for the condition table",
                ),
            ),
        ),
        Section(
            0,
            "7-requirements.md",
            "7. REQUIREMENTS — one row per goal leaf",
            (
                Text(
                    "Exactly one EARS pattern; all three of Scale/Meter/Target; exactly one verification "
                    "method; no machine noun in the statement."
                ),
                Table(
                    "7-requirements.rows",
                    (
                        _c("rn", "Rn", "R1, R2, ..."),
                        _c(
                            "ears",
                            "Pattern (EARS)",
                            "Ubiquitous / Event-driven / State-driven / Unwanted behaviour / Optional feature",
                        ),
                        _c(
                            "statement",
                            "Statement",
                            "the requirement, business vocabulary only",
                        ),
                        _c("scale", "Scale", "what is measured"),
                        _c("meter", "Meter", "how it is measured"),
                        _c("target", "Target", "the number or state"),
                        _c(
                            "verification",
                            "Verification",
                            "test / inspection / analysis / demonstration",
                        ),
                        _c("refines", "Refines", "the goal leaf, G1.1.1"),
                        _c("disposition", "Disposition", "kept / excluded / deferred"),
                    ),
                    "Add one row per requirement.",
                    instrument="EARS (Mavin et al., 2009) + fit criterion (Gilb)",
                    min_rows=1,
                    rule="exactly one EARS pattern; Scale, Meter and Target all present; exactly one "
                    "verification method; no machine noun; Refines a goal leaf",
                ),
                Text("## Acceptance Criteria — ACn"),
                Table(
                    "7-requirements.acceptance",
                    (
                        _c("acn", "ACn", "AC1, AC2, ..."),
                        _c("rn", "Rn", "the requirement it checks"),
                        _c("check", "Check", "one observable check"),
                    ),
                    "One acceptance criterion per requirement, one-to-one.",
                    instrument="traceability",
                    min_rows=1,
                    rule="one acceptance criterion per Rn; every criterion names its Rn",
                ),
                Field(
                    "7-requirements.notes",
                    "Notes:",
                    "the pattern/verification tallies and any derivation prose",
                ),
            ),
        ),
        Section(
            0,
            "8-constraints.md",
            "8. CONSTRAINTS — the ledger",
            (
                Text(
                    "State the contract before designing it. Classify each Cn Fixed / Negotiable / Unknown; "
                    "tag every Unknown `[NEEDS CONFIRM]`."
                ),
                Table(
                    "8-constraints.rows",
                    (
                        _c("cn", "Cn", "C1, C2, ..."),
                        _c("sentence", "Sentence", "the constraint"),
                        _c("class", "Class", "Fixed / Negotiable / Unknown"),
                        _c("value", "Value or number", "the number, or —"),
                        _c("confirm", "[NEEDS CONFIRM]", "the assumption, or —"),
                        _c("critical", "Critical-path?", "yes / no"),
                        _c("loadbearing", "Load-bearing?", "yes / no"),
                        _c(
                            "signpost",
                            "Signpost if it dies",
                            "what breaks if it is dropped",
                        ),
                    ),
                    "Add one row per constraint.",
                    instrument="constraint classification (Meyer); ledger sufficiency",
                    min_rows=1,
                    rule="classify every row Fixed / Negotiable / Unknown; no critical-path "
                    "[NEEDS CONFIRM] left open",
                ),
                Field(
                    "8-constraints.notes",
                    "Notes:",
                    "blank-classification count, the load-bearing set, and any derivation prose",
                ),
            ),
        ),
        Section(
            0,
            "9-exclusions.md",
            "9. EXCLUSIONS — the declared boundary",
            (
                Text("What is out, why, and what would change that."),
                Table(
                    "9-exclusions.rows",
                    (
                        _c("xn", "Xn", "X1, X2, ..."),
                        _c("excluded", "Excluded", "the thing left out"),
                        _c("why", "Why it is out", "YAGNI / out of scope / decided"),
                        _c(
                            "changes",
                            "What would change that",
                            "the trigger that brings it back",
                        ),
                    ),
                    "Add one row per exclusion.",
                    instrument="exclusion boundary",
                    min_rows=1,
                    rule="every exclusion carries a reason and what would change it",
                ),
                Field(
                    "9-exclusions.notes",
                    "Notes:",
                    "the boundary note, and any derivation prose",
                ),
            ),
        ),
        Section(
            0,
            "10-obstacles-misuse-unknowns.md",
            "10. OBSTACLES, MISUSE, UNKNOWNS",
            (
                Text(
                    "Obstacles refine until resolved by a requirement or excluded with a reason."
                ),
                Table(
                    "10-obstacles.obstacles",
                    (
                        _c("o", "O#", "O1, O2, ..."),
                        _c("obstructs", "Obstructs (goal)", "the goal it blocks"),
                        _c("condition", "Condition", "when it blocks"),
                        _c(
                            "resolution",
                            "Resolution (Rn / Xn / —)",
                            "the resolving requirement or exclusion",
                        ),
                    ),
                    "Add one row per obstacle.",
                    instrument="KAOS obstacles",
                    min_rows=1,
                    rule="resolve every obstacle by an Rn or an Xn with a written reason",
                ),
                Table(
                    "10-obstacles.misuse",
                    (
                        _c("m", "M#", "M1, M2, ..."),
                        _c("actor", "Actor", "who"),
                        _c("defeats", "How it defeats this", "the misuse"),
                        _c(
                            "disposition",
                            "Disposition",
                            "accepted / rejected / mitigated",
                        ),
                    ),
                    "Add one row per misuse case.",
                    instrument="misuse cases",
                    min_rows=0,
                ),
                Text(
                    "Boundary value (Myers): for every quantified target — zero / max / empty / duplicate."
                ),
                Table(
                    "10-obstacles.boundaries",
                    (
                        _c("target", "Target", "the quantified target"),
                        _c("zero", "zero", "the behaviour at zero"),
                        _c("max", "max", "the behaviour at max"),
                        _c("empty", "empty", "the behaviour when empty"),
                        _c("duplicate", "duplicate", "the behaviour on duplicates"),
                    ),
                    "Add one boundary row per quantified target.",
                    instrument="boundary value (Myers, 1979)",
                    min_rows=1,
                    rule="one row per quantified target: zero / max / empty / duplicate",
                ),
                Field(
                    "10-obstacles.notes",
                    "Notes:",
                    "the obstacle/misuse summary, and any derivation prose",
                ),
            ),
        ),
        Section(
            0,
            "11-traceability.md",
            "11. TRACEABILITY",
            (
                Text(
                    "Forward: every Rn reaches a test. Backward: every test names its Rn. A row you "
                    "cannot complete is the defect."
                ),
                Table(
                    "11-traceability.rows",
                    (
                        _c("rn", "Rn", "the requirement"),
                        _c("goal", "Goal", "the goal leaf"),
                        _c("cn", "Cn", "the constraints it rests on"),
                        _c("xn", "Xn", "the exclusions it respects"),
                        _c("acn", "ACn", "its acceptance criterion"),
                        _c("scenario", "Scenario", "the specifier's scenario, or —"),
                        _c("contract", "Contract", "the contract, or —"),
                        _c("test", "Test", "the test that closes it"),
                    ),
                    "Add one row per requirement.",
                    instrument="traceability matrix",
                    min_rows=1,
                    rule="every Rn has a row and names the test that closes it",
                ),
                Field(
                    "11-traceability.notes",
                    "Notes:",
                    "the forward/backward note, and any derivation prose",
                ),
            ),
        ),
        Section(
            0,
            "12-stop-test.md",
            "12. STOP TEST — every count must be zero",
            (
                Text(
                    "Computed from the rendered record. Run `harness.py check interrogator`."
                ),
                Computed("12-stop-test.result", "Result:", render_stop_test),
            ),
        ),
        Section(
            0,
            "decisions.md",
            "DECISIONS — for the operator",
            (
                Text(
                    "Number every candidate case and every `[NEEDS CONFIRM]` as a DECISION naming the "
                    "instrument that forced it, with its options."
                ),
                Table(
                    "decisions.rows",
                    (
                        _c("dn", "Dn", "D1, D2, ..."),
                        _c(
                            "instrument",
                            "Instrument",
                            "the named rule that forces the decision",
                        ),
                        _c("question", "Question", "the bounded question"),
                        _c(
                            "options",
                            "Options",
                            "a / b / c — start each option on its own line; a `|` breaks the table",
                        ),
                        _c("answer", "Operator answer", "filled after the gate"),
                    ),
                    "Add one row per decision.",
                    instrument="decision ownership",
                    min_rows=0,
                    rule="every DECISION names the instrument that forces it and its options; "
                    "separate the options with `/` — a `|` breaks the table",
                ),
                Field(
                    "decisions.notes",
                    "Notes:",
                    "the gate note, and any derivation prose",
                ),
            ),
        ),
        Section(
            0,
            "13-record-note.md",
            "13. RECORD NOTE — the accepted record prose and the handoff",
            (
                Text(
                    "The prose the accepted record carries beyond the tables, and the two handoff "
                    "fields. The `01-interrogator/` sections are the home of the requirement facts. "
                    "There is no root projection file. Keep neutral repo prose: no pack, role, "
                    "process or provenance word."
                ),
                Field(
                    "bp.overview",
                    "Record overview:",
                    "one paragraph: what changes and what stands",
                ),
                Field(
                    "bp.goal-note",
                    "Goal fit-criterion prose:",
                    "the fit criterion in prose, naming its Rn",
                ),
                Field(
                    "bp.leaf-note",
                    "Goal-tree leaf note:",
                    "why every leaf is satisfiable by one agent",
                ),
                Field(
                    "bp.vocab",
                    "Constraints vocabulary:",
                    "the terms the record fixes, one line each",
                ),
                Field(
                    "bp.ledger-note",
                    "Constraints closing note:",
                    "blank classifications, critical-path confirms, the load-bearing set",
                ),
                Field(
                    "bp.requirements-note",
                    "Requirements note:",
                    "what the requirements carry and what stays in constraints",
                ),
                Field(
                    "bp.trace-note",
                    "Traceability note:",
                    "forward and backward, and the document home",
                ),
                Field(
                    "bp.exclusions-note",
                    "Exclusions closing note:",
                    "the [NEEDS CONFIRM] status of the boundary",
                ),
                Field(
                    "proto.frozen",
                    "FROZEN HANDOFF:",
                    "the facts the specifier must not reopen",
                ),
                Field(
                    "proto.risks",
                    "OPEN RISKS:",
                    "requirement defaults and assumptions, or `none`",
                ),
            ),
        ),
    )


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
