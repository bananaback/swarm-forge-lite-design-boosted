# modeler — design answer

The modeler's final message. Design-native: the forms are the output; this message is the
handoff boundary and the decision ledger.

```
TASK: <stable task name>
ROLE: modeler
STATE: settled | open | blocked
WORK: design/<task>/work/02-modeler.md
PRODUCED: CRC_CARDS REV 1 [ACCEPTED]
PRODUCED: SECRETS REV 1 [ACCEPTED]
PRODUCED: CORE_SHELL_MAP REV 1 [ACCEPTED]
PRODUCED: DEPENDENCY_GRAPH REV 1 [ACCEPTED]
PRODUCED: STATE_MAP REV 1 [ACCEPTED]
STOP TEST: a second grammar pass adds zero entries; every acceptance check walks card-to-card with no gap; one secret per card; no Core->concrete-Shell edge; acyclic; no SRP sentence with "and"; every sequence names a state owner -> pass | fail
DECISIONS: <n>
  D1 [<named rule: Parnas merge/split, SRP split, DIP seam, ambiguous noun>] <question> | options: <a> | <b> | <c> | answer: <operator's>
FROZEN HANDOFF: <the closed secret the contractor must not reopen, e.g. "FrameDecoder guards the wire format; core never sees a byte buffer">
REVISION REQUESTS: <"[section] — reason — route to <role>" or "none">
OPEN RISKS: <design assumptions and non-blocking defaults, or "none">
NEXT: contractor
```

Good: five `PRODUCED` lines `[ACCEPTED]`, one `DECISIONS` item per domain-shape merge/split with
its rule named, `STOP TEST … -> pass`.
Bad: a card with two unrelated secrets, a Core card calling a concrete Shell class, or an SRP
sentence containing "and".

`STATE: settled` means the operator resolved every domain-shape `DECISION` at the `question` gate.
Mechanical synonym merges are resolved by the modeler and logged in the work file, not gated.
`NEXT` names the role the orchestrator dispatches; the modeler never calls it.
