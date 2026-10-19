from __future__ import annotations

from questions_engine import (
    Field,
    Matrix,
    Section,
    Table,
    Text,
    _c,
)

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


def _interrogator_sections_a() -> tuple[Section, ...]:
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
    )
