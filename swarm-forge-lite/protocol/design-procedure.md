# Design Procedure - Step Index

The requirement and design method, as an index. The **detailed actions live in the
`<workflow>` of each role** (forged into the agent). This file maps the steps, so
any role can see the whole. The front end (F1-F13) runs before and across the
specifier. The design steps (1-16) belong to the design team. Definitions are in
`reference/design-craft-front.md` (front end) and `reference/design-craft-design.md`
(design). Stop tests, ownership, loop control, and the handoff rule are in
`reference/design-quality.md`. The freeze and the parallel split are in
`reference/module-rules.md`. Input, output, working state, and editing rules are in
`protocol/design-protocol.md`. The empty forms are in `design/templates/`.

## Position in the Pipeline

```
operator intent (+ any draft requirement - an input, never an authority)
  -> interrogator     resolves the requirement document first (refine a draft, or create
                      docs/specs/NN-<subsystem>.md), then the requirement record: measurable goal,
                      SCR behavior tables, constraint ledger, exclusions, traceability
                                                                        (operator-gated)
  -> specifier        inspects the record as a second party, then writes business Gherkin only
  -> architect        cuts the subsystem into modules and freezes the interfaces   (operator-gated)
  -> designer x N     one module each, in parallel                               (one batched gate)
  -> critic           reads the union, writes the subsystem SKELETON                  (operator-gated)
  -> coder            fills method bodies against the accepted contracts
  -> refactorer       minor in-place cleanup; terminal gate
```

The interrogator fixes what is required and why, in tables that you can check. The
specifier reads that document and the record, fixes what the business observes, and
is the second pair of eyes on the record. The architect fixes the structure and the
modules. The designers fix the internals of one module each. The critic reviews
the union. The coder writes the bodies. Gherkin belongs to the specifier and is never
written during the requirement work or the design.

## Front-End Index

| Step | Role | Technique | Output |
|---|---|---|---|
| F1 Frame: the world, not the machine | interrogator | perfect-technology filter; context-free questions (Gause & Weinberg, 1989) | FRAME |
| F2 Measurable goal | interrogator | measurable-goal template + fit criterion (Gilb, 1988) | GOAL |
| F3 Goal refinement | interrogator | KAOS AND/OR refinement (Dardenne, van Lamsweerde, Fickas, 1993) | GOAL TREE |
| F4 Variables | interrogator | four-variable model (Parnas et al., 1978) | VARIABLES |
| F5 Behavior tables | interrogator | SCR mode transition / event / condition tables | TABLES |
| F6 Completeness and disjointness | interrogator | SCR table properties | pass / fail |
| F7 Requirements | interrogator | EARS patterns (Mavin et al., 2009) + fit criterion | REQUIREMENTS |
| F8 Ledger and exclusions | interrogator | constraint classification (Meyer) + exclusions | CONSTRAINTS - EXCLUSIONS |
| F8B **Scope gate** | interrogator | near-term use cases and scale; YAGNI (Beck Rule 4) | EXCLUSIONS - CONSTRAINTS |
| F9 Unknowns | interrogator | KAOS obstacles and anti-goals; misuse cases; boundary value (Myers, 1979) | discharge |
| F10 Traceability | interrogator | Rn -> ACn, both directions | TRACEABILITY |
| F11 Stop test | interrogator | the zero-count rubric (`design-quality.md`) | pass / fail |
| F12 Inspection | specifier | Fagan (1976): the author does not inspect their own record | defect list or clean |
| F13 Acceptance spec | specifier | Cockburn's main success scenario + numbered extensions (2001) | feature |

## Design Step Index

| Step | Role | Technique | Output |
|---|---|---|---|
| 1 Freeze the ask | interrogator | measurable-goal template | GOAL |
| 2 Constraint ledger + sufficiency gate | interrogator | ledger + sufficiency gate | CONSTRAINTS |
| 3 Grammar decomposition | architect | Abbott noun-verb (1983); cross-cutting-verb rule | grammar table |
| 4 CRC grouping | architect | CRC cards (Beck & Cunningham, 1989) | CRC_CARDS |
| 5 Secret assignment | architect | Parnas information hiding (1972) | SECRETS |
| 6 Core/Shell tagging | architect | functional core / imperative shell | CORE_SHELL_MAP |
| 7 Dependency graph + inversion | architect | DIP, "core needs X, shell satisfies X" | DEPENDENCY_GRAPH |
| 8 Single responsibility check | architect | SRP | SRP sentences |
| 8A State & ordering pass | architect | explicit state/transition ownership | STATE_MAP |
| 8B **Module cut + interface freeze** | architect | Parnas secrets + caller closure + the freeze checklist (`module-rules.md`) | ARCHITECTURE - INTERFACES |
| 9 Contracts per method | designer | Design by Contract (Meyer, 1988) + CQS | CONTRACTS |
| 10 Collaboration wiring | designer | Tell, Don't Ask + Law of Demeter | revised sketches |
| 11 Passes-the-tests gate | designer | Beck Rule 1; design<->business seam | TEST_MAP |
| 12 Extension rehearsal | designer (design), critic (verify) | OCP | seam or YAGNI note |
| 13 Substitutability & trim | designer (design), critic (verify) | LSP + ISP | trimmed interfaces |
| 14 Duplication & minimalism | designer (design), critic (verify) | Beck Rules 3 & 4; caller closure | minimal module skeleton |
| 15 Reveals-intention pass | designer | Beck Rule 2 | module SKELETON |
| 16 **Cross-module integration** | critic | cross-module dedup + interface check | subsystem SKELETON |

Steps 3-8B run once for the subsystem, at the architect. Steps 9-15 run once for each
module, in parallel, at the designers. Step 16 runs once, at the critic, over the
union. The critic **verifies** the techniques of steps 12-14 across the modules; the
designer designs them for its own module.

Step 8B honors the **scope gate** (F8B). A module cut and an interface earn their
keep: a guard, a boundary, or a scope answer. Do not cut a module or freeze an
interface for a use case the scope gate excludes. Economy (Beck Rule 4) removes
structure that is not a guard. It never removes a type, a contract, a test, or an
invariant.
