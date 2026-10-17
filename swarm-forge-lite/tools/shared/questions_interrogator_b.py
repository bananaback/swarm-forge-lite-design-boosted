from __future__ import annotations

from questions_engine import (
    Computed,
    Field,
    Section,
    Table,
    Text,
    _c,
    render_stop_test,
)


def _interrogator_sections_b() -> tuple[Section, ...]:
    return (
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
