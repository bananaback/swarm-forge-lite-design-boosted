# Design Quality - gates, stop tests, ownership

Read on demand: the literal stop test definitions. This file is the **single
source** for the stop tests. The design envelope and the role prompts point here.
They never copy a stop test. The freeze and the parallel split are in
`module-rules.md`.

## Stop tests (per role) - literal pass/fail

- **interrogator:** SCR **completeness** - every mode x event has a transition
  entry. SCR **disjointness** - no mode x event has two. Every event x condition
  resolves to exactly one value. One agent satisfies every goal leaf, or the record
  excludes it explicitly. Zero undischarged obstacles, and each one carries a
  resolving requirement or a written exclusion reason. Every top goal has an
  anti-goal. Every requirement matches exactly one EARS pattern. Every requirement
  carries Scale/Meter/Target. Every requirement names exactly one verification
  method. Zero blank constraint classifications. No critical-path `[NEEDS CONFIRM]`
  remains. The vocabulary in GOAL/CONSTRAINTS can express every acceptance check.
  Every candidate case carries the disposition of the operator. The requirement
  document (`docs/specs/NN-<subsystem>.md`) exists - refined when a draft existed,
  created when one did not - and matches the accepted record.
  The interrogator computes this with `harness.py check interrogator` (the rendered
  record) and `harness.py lint-record --subsystem <subsystem>` (the record projection).
  Every count is a finding code, and the role fixes a finding by changing one
  answer, never by a new derivation of the record.
- **architect:** A second grammar pass adds zero entries. Every acceptance check
  walks card-to-card with no gap. No card has zero responsibilities. Each card has
  one secret. No Core -> concrete-Shell edge. The graph is acyclic. No SRP sentence
  contains "and". Every sequence-shaped check names a state owner. **The module map
  is frozen:** the write sets are disjoint, the Provides/Requires graph is acyclic,
  every shared edge has a frozen interface, and every shared file is named. Every
  module and every interface earns its keep: a guard, a boundary, or a scope answer.
  No module cut and no interface for a future the scope gate excludes.
- **designer:** Every method has pre/post/invariant and exactly one CQS tag. No call
  chain exceeds one dot past self/param/local. Every acceptance check has a named
  test that is wired to an existing signature. Every OCP seam is built now or has a
  written YAGNI reason. No implementer violates a contract. No interface method is
  unused by every client. Zero duplicated policy in the module. Zero classes outside
  the caller closure. Every name is self-explanatory when you read it with its
  contract alone. Every class, seam, and helper earns its keep: a guard, a boundary,
  or a scope answer. **The module honors every frozen interface.**
- **critic:** At least one exclusion slots in by addition only, or has a written
  YAGNI reason. No implementer violates a contract. No interface method is unused by
  every client. Zero duplicated policy **across the modules**. Zero classes outside
  the caller closure. Every name is self-explanatory when you read it with its
  contract alone. Every extension point cites a scope answer, or it is an exclusion
  with a reason. **Every module honored its frozen interface, and the subsystem
  `SKELETON.md` is the union with no cross-module duplication.**

## Chunk clauses and the module gate

Every stop test above has two parts.

- **The chunk clauses.** The clauses the delta can affect. The dispatch cites
  these; the role declares pass on them, and fixes one answer for each finding.
- **The module gate.** The full list above. `swarm.check <role>` computes it. The
  orchestrator runs it at the module gate, after the role settles.

The chunk clauses for each role:

- **interrogator** - the SCR rows, requirements, exclusions, and counts the delta touches.
- **architect** - the boundary-freeze checklist and the cards the delta touches.
- **designer** - the contract, CQS, named-test, and caller-closure clauses of its module.
- **critic** - the cross-module dedup and the union clauses over the changed modules.

## Go-to-code condition
Hand to the coder only when all hold: the module map is frozen and every shared
edge carries a frozen interface. Every class has one secret and one responsibility
sentence. Every method has a contract, one CQS tag, and a wired test. Zero Core ->
concrete-Shell edges. Zero classes outside the caller closure. Every GOAL/Cn
acceptance check has a named test.

## Decision ownership

| The operator decides | The role decides alone and logs |
|---|---|
| **The scope gate: the near-term use cases, the expected scale, and what is out - interrogator** | YAGNI: whether a proposed extension point cites a scope answer - architect and critic |
| Brainstormed cases (accept/reject/modify) - interrogator | Exact-synonym merges - architect |
| A business contradiction the record cannot settle - any role | Domain-shape card merges and splits - architect |
| An OCP seam for a FUTURE use case: build it now, or not - critic | Module cut, module merge, or `Owns` move - architect, with its rule (Parnas/SRP/DIP/two-way door) |
| Skeleton acceptance - critic | Public-shape Command/Query splits - designer |
| | Internal Demeter forwarding - designer |
| | An LSP, dedup or naming fix that moves no public contract - designer and critic |

**The one test:** raise a DECISION when the answer changes a **behavior, a constraint,
an exclusion, or the scope**. Every other choice is the ROLE'S: write the answer in
the row, and continue. A design-internal choice never stops the pipeline.

## Loop control
- A rejected decision or a downstream discovery calls again only the owning role,
  scoped to the affected module or section and its direct collaborators.
- **A `CONFLICT` returns to the architect.** The architect amends, rejects, or
  reassigns (`module-rules.md`). The orchestrator then re-dispatches only the
  consumers named in the changed interface file.
- **Containment stops at the module cut.** A module cut, an `Owns` move, or a
  frozen interface change invalidates every affected designer: run the architect
  again, then every designer it reaches. Do not pretend that the edit was contained.
- **Containment stops at the goal.** A GOAL or critical-path-constraint change
  invalidates every derived section: run the interrogator again, then the specifier,
  the architect, and every affected designer.
- Edit a section file in place. Add every row, entry, and section that the work
  needs. Write no bookkeeping about the edit: no version number, no status flag, no
  change log.

## Handoff to the coder
The name of one method, its contract, and its responsibility sentence are the whole
prompt. They live in `design/subsystems/<subsystem>/SKELETON.md`, projected
self-contained by `swarm.genRecord` from the accepted module skeletons, with the
critic's brief at the top. The coder and the refactorer read
that file and never open the record. If the coder needs more context to write the
body, the contract was underspecified: fix the contract. Do not pad the prompt.

## Contrastive examples

**A DECISION item - good / bad**
```
Good: D3 [Parnas] Ledger and Audit both guard the storage format - merge the two
      modules, or split on append-vs-read? | options: merge | split | answer: split
Bad:  D3 [decision] Should we refactor this? | options: yes | no
```

**A CRC responsibility - good / bad**
```
Good: "Reserve stock and report the shortfall."
Bad:  "Handles inventory and also updates the ledger."
```

**A designer's stop test claim - good / bad**
```
Good: STOP TEST: 6/6 methods tagged; 0 Demeter chains; 0 freeze conflicts -> pass
Bad:  STOP TEST: looks clean -> pass
```
