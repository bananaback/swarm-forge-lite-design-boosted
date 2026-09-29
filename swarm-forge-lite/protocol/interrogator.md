# interrogator — requirement answer

The interrogator's final message. Requirement-native: no `VERIFY` command, no `FILES` diff,
no `SUMMARY`. Its full output is the filled work file; this message is the decision ledger.
It runs **before the specifier**.

```
TASK: <stable task name>
ROLE: interrogator
STATE: settled | open | blocked
DRAFT: <the draft requirement path audited, or none>
SPEC: <docs/specs/NN-<task>.md> REV <n> [refined | created]
WORK: design/<task>/work/01-interrogator.md
PRODUCED: GOAL REV 1 [ACCEPTED]
PRODUCED: CONSTRAINTS REV 1 [ACCEPTED]
PRODUCED: EXCLUSIONS REV 1 [ACCEPTED]
PRODUCED: REQUIREMENTS REV 1 [ACCEPTED]
TABLES: modes <n> · events <n> · conditions <n> · complete and disjoint -> pass | fail
STOP TEST: <the counts of WORK §12> -> pass | fail
DECISIONS: <n>
  D1 [<instrument>] <question> | options: <a> | <b> | <c> | answer: <operator's>
FROZEN HANDOFF: <the facts the specifier must not reopen, e.g. the run is refused when the blur list is empty>
REVISION REQUESTS: <"[section] — reason — route to <role>" or "none">
OPEN RISKS: <requirement defaults and assumptions, or "none">
NEXT: specifier
```

Good: `STATE: settled`, four `PRODUCED` lines each `[ACCEPTED]`, `SPEC: docs/specs/04-safety-rule-engine.md REV 2 [created]`,
`TABLES: modes 3 · events 5 ·
conditions 4 · complete and disjoint -> pass`, `DECISIONS: 6` each naming the instrument that
forced it, `STOP TEST: … -> pass`.

Bad: `STATE: settled` with a non-zero stop-test count, an undischarged obstacle, a table cell
closed with an invented requirement, a `SPEC` naming a document that does not exist or does not
match the record, or a `DECISION` that does not name its instrument.

`SPEC` is the requirement document in the project's requirements workplace (`docs/specs/NN-<task>.md`,
resolved from the `SPECS` row of `harness.py status` — the `specs` field in `harness.json`; never
hardcoded here). It reads as a plain requirements document for the repo: no reference to this pack,
a blueprint, a role, a revision, a decision, a stop test, or any process — a reader must not be able
to tell what produced it.
The interrogator resolves its existence with the operator before framing — it never assumes a
draft is absent, and never treats a draft it finds as authority. An existing draft is refined;
when none exists the document is created from the accepted record, one-to-one with Rn/ACn.

`STATE: settled` means every stop-test count is zero, the tables are complete and disjoint, the
requirement document matches the accepted record, and the operator answered every `DECISION` at the
`question` gate. On a missing critical fact,
`STATE: blocked` with the fact in `OPEN RISKS`. `NEXT` names the role the orchestrator dispatches;
it is `specifier`, never a design role, and the interrogator never calls it.
