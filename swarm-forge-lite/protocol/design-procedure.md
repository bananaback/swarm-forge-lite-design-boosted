# Design Procedure — step index

The requirement and design method, as an index. The **detailed actions live in each role's
`<workflow>`** (forged into the agent); this file maps the steps so any role can see the
whole. The front end (F1–F13) runs before and across the specifier; the design steps (1–15)
are the design team's. Definitions are in `reference/design-craft-front.md` (front end) and `reference/design-craft-design.md` (design); stop tests, ownership, loop control,
and the handoff rule are in `reference/design-quality.md`; input/output, working state, and
revisions are in `protocol/design-protocol.md`; empty forms are in `design/templates/`.

## Position in the pipeline

```
operator intent (+ any draft requirement — an input, never an authority)
  -> interrogator     resolves the requirement document with the operator first (an existing
                      draft is refined, none is created at docs/specs/NN-<task>.md), then the
                      requirement record: measurable goal, SCR behaviour tables,
                      constraint ledger, exclusions, traceability        (operator-gated)
  -> specifier        inspects the record as a second party, then writes business Gherkin only
  -> [design gate]    modeler -> contractor -> critic                   (operator-gated)
  -> coder            fills method bodies against the accepted contracts
  -> refactorer       minor in-place cleanup; terminal gate
```

The interrogator fixes what is required and why, in tables that can be checked. It opens by
resolving the requirement document with the operator: an existing draft is refined, and none means
the interrogator creates `docs/specs/NN-<task>.md`. The specifier then reads that doc and the
record, fixes what the business observes, and is the second pair of eyes on the record. The design team
fixes how the code is shaped to provide it. The coder writes bodies. Gherkin belongs to the
specifier and is never written during the requirement work or the design.

## Front-end index

| Step | Role | Technique | Output |
|---|---|---|---|
| F1 Frame: the world, not the machine | interrogator | perfect-technology filter; context-free questions (Gause & Weinberg, 1989) | FRAME |
| F2 Measurable goal | interrogator | measurable-goal template + fit criterion (Gilb, 1988) | GOAL |
| F3 Goal refinement | interrogator | KAOS AND/OR refinement (Dardenne, van Lamsweerde, Fickas, 1993) | GOAL TREE |
| F4 Variables | interrogator | four-variable model (Parnas et al., 1978) | VARIABLES |
| F5 Behaviour tables | interrogator | SCR mode transition / event / condition tables | TABLES |
| F6 Completeness and disjointness | interrogator | SCR table properties | pass / fail |
| F7 Requirements | interrogator | EARS patterns (Mavin et al., 2009) + fit criterion | REQUIREMENTS |
| F8 Ledger and boundary | interrogator | constraint classification (Meyer) + exclusions | CONSTRAINTS · EXCLUSIONS |
| F9 Unknowns | interrogator | KAOS obstacles and anti-goals; misuse cases; boundary values (Myers, 1979) | discharge |
| F10 Traceability | interrogator | Rn → ACn, both directions | TRACEABILITY |
| F11 Stop test | interrogator | the zero-count rubric (`design-quality.md`) | pass / fail |
| F12 Inspection | specifier | Fagan (1976): the author does not inspect their own record | defect list or clean |
| F13 Acceptance spec | specifier | Cockburn's main success scenario + numbered extensions (2001) | feature |

## Design step index

| Step | Role | Technique | Output |
|---|---|---|---|
| 1 Freeze the ask | interrogator | measurable-goal template | GOAL |
| 2 Constraint ledger + sufficiency gate | interrogator | ledger + sufficiency gate | CONSTRAINTS |
| 3 Grammar decomposition | modeler | Abbott noun-verb (1983); cross-cutting-verb rule | grammar table |
| 4 CRC grouping | modeler | CRC cards (Beck & Cunningham, 1989) | CRC_CARDS |
| 5 Secret assignment | modeler | Parnas information hiding (1972) | SECRETS |
| 6 Core/Shell tagging | modeler | functional core / imperative shell | CORE_SHELL_MAP |
| 7 Dependency graph + inversion | modeler | DIP, "core needs X, shell satisfies X" | DEPENDENCY_GRAPH |
| 8 Single responsibility check | modeler | SRP | SRP sentences |
| 8A State & ordering pass | modeler | explicit state/transition ownership | STATE_MAP |
| 9 Contracts per method | contractor | Design by Contract (Meyer, 1988) + CQS | CONTRACTS |
| 10 Collaboration wiring | contractor | Tell, Don't Ask + Law of Demeter | revised sketches |
| 11 Passes-the-tests gate | contractor | Beck Rule 1; design↔business seam | TEST_MAP |
| 12 Extension rehearsal | critic | OCP | seam or YAGNI note |
| 13 Substitutability & trim | critic | LSP + ISP | trimmed interfaces |
| 14 Duplication & minimalism | critic | Beck Rules 3 & 4; caller closure | minimal skeleton |
| 15 Reveals-intention pass | critic | Beck Rule 2 | SKELETON, and `SKELETON.md` for the coder |
