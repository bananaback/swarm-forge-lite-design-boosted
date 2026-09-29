# interrogator work — <task>

WORK: design/<task>/work/01-interrogator.md
REV: 1
DRAFT: <path to the draft requirement, or "none">
SPEC: docs/specs/NN-<task>.md — refined | created   (the repo workplace; the gate's doc deliverable)

Methods: `<pack>/reference/design-craft-front.md`, `<pack>/reference/design-quality.md`
(your stop test). Fill every table. A cell you cannot fill is a finding, not a blank.

---

## 0A. SPEC — the requirement document

Path: the requirements workplace, `docs/specs/NN-<task>.md` — resolved from the `SPECS` row of
`harness.py status` (the `specs` field in `harness.json`), never hardcoded here. Resolve it before framing: if the
dispatch names a draft, read it; if it says none, ask the operator whether one exists and where —
never assume. Refine an existing draft to match the accepted record; create the doc when none
exists. House shape: `# NN — <name>`, then Purpose · Scope (in/out) · Definitions · Requirements
(`- Rn — <statement>`) · Acceptance Criteria (`- ACn — <check>`) · Constraints. One-to-one with the
record's Rn/ACn, business vocabulary only, no machine noun in a requirement statement. It reads as a
plain requirements document for the repo: no reference to this pack, a blueprint, a role, a
revision, a decision, a stop test, or any process — a reader must not be able to tell what produced
it. The blueprint stays the record of authority if the two disagree.

Decisions on the doc: <what changed in a refined draft, in one line per change; or "created">

---

## 0. FRAME — requirement, not design

Real client: <who decides, separately from who asks>
Definition of success: <what would make them say it worked>
The world that must change: <phenomena outside the machine>

| Context-free question (Gause & Weinberg) | Answer, or `[NEEDS CONFIRM]` |
|---|---|
| What is the real reason for this ask? | |
| What is a successful solution? | |
| What would make it fail? | |
| Who decides? | |

Perfect-technology filter: describe the behaviour as if the machine were free and instantaneous.

| Sentence that leaked design | Sent back as |
|---|---|
| | |

## 1. GOAL — fit criterion (Gilb)

When <trigger>, the system shall <outcome>, verified by <observable check>.

- Scale: <what is measured>
- Meter: <how it is measured>
- Target: <the number or state that must hold>

Unmeasurable verbs found and rejected: <list or "none">

## 2. GOAL TREE — KAOS refinement

| Node | Type (G/R/O/A/X) | Statement | Refines (parent) | Disposition |
|---|---|---|---|---|
| | | | | |

Rule: refine AND/OR until every leaf is satisfiable by **one agent** — that leaf is a requirement.
Every top goal carries one anti-goal.

| Anti-goal | Against goal | We would have failed if |
|---|---|---|
| | | |

## 3. VARIABLES — the four-variable model (SCR)

| Monitored (env → system) | Controlled (system → env) | Input (internal, derived) | Output (internal, derived) |
|---|---|---|---|
| | | | |

Rule: a requirement relates **monitored and controlled variables only** — never internals.

## 4. MODE TRANSITION TABLE (SCR)

`@` = any. **Completeness:** every mode × event has an entry. **Disjointness:** none has two.

| mode \ event | <event A> | <event B> | <event C> |
|---|---|---|---|
| <mode 1> | | | |
| <mode 2> | | | |

## 5. EVENT TABLE (SCR)

`@T` when the condition becomes true · `@F` when it becomes false · `@C` when it changes.

| Event | Condition | When | Response |
|---|---|---|---|
| | | | |

## 6. CONDITION TABLE (SCR)

| Condition \ mode | <mode 1> | <mode 2> |
|---|---|---|
| | | |

## 7. REQUIREMENTS — one row per goal leaf

| Rn | Pattern (EARS) | Statement | Scale | Meter | Target | Verification (test / inspection / analysis / demonstration) | Refines | Disposition |
|---|---|---|---|---|---|---|---|---|
| | | | | | | | | |

Rules: exactly one EARS pattern; all three of Scale/Meter/Target; exactly one verification method;
no machine noun in the statement (no class, module, file, or framework name).

## 8. CONSTRAINTS — the ledger (state the contract before designing it)

| Cn | Sentence | Fixed / Negotiable / Unknown | Value or number | [NEEDS CONFIRM] assumption | Critical-path? | Load-bearing? | Signpost if it dies |
|---|---|---|---|---|---|---|---|
| | | | | | | | |

## 9. EXCLUSIONS — the declared boundary

| Xn | Excluded | Why it is out | What would change that |
|---|---|---|---|
| | | | |

## 10. OBSTACLES, MISUSE, UNKNOWNS

| O# | Obstructs (goal) | Condition | Resolution (Rn / Xn / —) |
|---|---|---|---|
| | | | |

| M# | Actor | How it defeats this | Disposition |
|---|---|---|---|
| | | | |

Boundary values (Myers): for every quantified target — zero / max / empty / duplicate.

| Target | zero | max | empty | duplicate |
|---|---|---|---|---|
| | | | | |

## 11. TRACEABILITY

| Rn | Goal | Cn | Xn | ACn | Scenario | Contract | Test |
|---|---|---|---|---|---|---|---|
| | | | | | | | |

Forward: every Rn reaches a test. Backward: every test names its Rn. A row you cannot complete
is the defect.

## 12. STOP TEST — every count must be zero

| Count | Value |
|---|---|
| modes × events with no transition entry (incompleteness) | |
| modes × events with two entries (non-disjoint) | |
| events × conditions resolving to no value or to two | |
| goal leaves not satisfied by one agent and not excluded | |
| undischarged obstacles (no resolving Rn, no exclusion reason) | |
| top goals with no anti-goal | |
| requirements matching no EARS pattern, or more than one | |
| requirements stated with a machine noun | |
| requirements missing Scale, Meter or Target | |
| requirements with no verification method, or more than one | |
| quantified targets with no boundary set | |
| blank constraint classifications | |
| critical-path `[NEEDS CONFIRM]` remaining | |
| acceptance checks needing vocabulary outside GOAL/CONSTRAINTS | |
| candidate cases with no operator disposition | |
| requirement documents that do not match the accepted record (refined or created) | |

## 13. DECISIONS — for the operator

| Dn | Instrument | Question | Options | Operator answer |
|---|---|---|---|---|
| | | | | |
