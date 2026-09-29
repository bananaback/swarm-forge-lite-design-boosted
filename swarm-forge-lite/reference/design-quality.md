# Design Quality — gates, stop tests, ownership

Read on demand. This holds the definitions the workflow checks against. The workflow
says "run the stop test"; this says exactly what the stop test is.

## Stop tests (per role) — literal pass/fail

- **interrogator:** SCR **completeness** — every mode × event has a transition entry; SCR
  **disjointness** — no mode × event has two; every event × condition resolves to exactly one
  value; every goal leaf is satisfied by one agent or explicitly excluded; zero undischarged
  obstacles (each carries a resolving requirement or a written exclusion reason); every top goal
  has an anti-goal; every requirement matches exactly one EARS pattern; every requirement carries
  Scale/Meter/Target; every requirement names exactly one verification method; zero blank
  constraint classifications; no critical-path `[NEEDS CONFIRM]` remains; every acceptance check
  is expressible with vocabulary already in GOAL/CONSTRAINTS; every candidate case carries the
  operator's disposition; the requirement document (`docs/specs/NN-<task>.md`) exists — refined
  when a draft existed, created when none did — and matches the accepted record.
- **modeler:** a second grammar pass adds zero entries; every acceptance check walks
  card-to-card with no gap; no card has zero responsibilities; one secret per card; no
  Core -> concrete-Shell edge; the graph is acyclic; no SRP sentence contains "and"; every
  sequence-shaped check names a state owner.
- **contractor:** every method has pre/post/invariant and exactly one CQS tag; no call
  chain exceeds one dot past self/param/local; every acceptance check has a named test
  wired to an existing signature.
- **critic:** at least one exclusion slots in by addition only, or has a written YAGNI
  reason; no implementer violates a contract; no interface method is unused by every
  client; zero duplicated policy; zero classes outside the caller closure; every name is
  self-explanatory read with its contract alone.

## Go-to-code condition
Hand to the coder only when all hold: every class has one secret; one responsibility
sentence; every method has a contract, one CQS tag, and a wired test; zero
Core -> concrete-Shell edges; zero classes outside the caller closure; every GOAL/Cn
acceptance check has a named test.

## Decision ownership

| The operator decides | The role decides alone and logs |
|---|---|
| Brainstormed cases (accept/reject/modify) | Exact-synonym merges |
| Domain-shape card merges/splits | Internal Demeter forwarding |
| Public-shape Command/Query splits | LSP/dedup/naming fixes that move no public contract |
| OCP seam: build now vs YAGNI | |
| Skeleton acceptance; business contradictions | |

## Loop control and revisions
- A rejected decision or a downstream discovery re-invokes only the owning role, scoped to
  the affected card/section and its direct collaborators. The change is a `[REVISION REQUEST]` line, never an in-place edit,
  and no log of it is kept — the artifact is the record.
- **Containment stops at the goal.** A GOAL or critical-path-constraint change invalidates
  every derived section: re-run the interrogator and re-validate downstream, from the first
  affected section. Do not pretend the edit was contained.
- Accepted text is immutable; a change increments REV and marks the changed span.

## Handoff to the coder
One method's name, its contract, and its responsibility sentence are the whole prompt. They live
in `design/<task>/SKELETON.md`, written self-contained by the critic; the coder and the refactorer
read that file and never open the blueprint. If the coder needs more context to write the body,
the contract was underspecified — fix the contract, do not pad the prompt.

## Contrastive examples

**A DECISION item — good / bad**
```
Good: D3 [Parnas] Ledger and Audit both guard the storage format — merge, or split on
      append-vs-read? | options: merge | split | answer: split
Bad:  D3 [decision] Should we refactor this? | options: yes | no
```

**A CRC responsibility — good / bad**
```
Good: "Reserve stock and report the shortfall."
Bad:  "Handles inventory and also updates the ledger."
```

**A modeler's stop test claim — good / bad**
```
Good: STOP TEST: second grammar pass added 0 entries; 7/7 acceptance checks walk with no
      gap; 0 Core->Shell edges -> pass
Bad:  STOP TEST: looks clean -> pass
```
